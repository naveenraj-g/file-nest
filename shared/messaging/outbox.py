"""
shared.messaging.outbox — Transactional outbox for reliable event publishing.

The transactional outbox pattern guarantees at-least-once NATS delivery even if
the process crashes between a DB commit and a NATS publish:

  1. Service calls `TransactionalOutboxPublisher.publish()` inside the same DB
     transaction as the business operation (e.g. creating a file record).
  2. Both the business row and the outbox row are committed atomically.
  3. A separate `OutboxWorker` process polls for undelivered rows, publishes
     each one to NATS JetStream, and marks it as `published_at = now()`.

Rules enforced by this design:
  - Services must NEVER call NATS directly. Use only this publisher.
  - The publisher does NOT flush or commit — the calling session owns that.
  - The OutboxWorker is the only component allowed to mark rows as published.

NATS subject format: `filenest.<org_id>.<project_id>.<event_type>`

Usage:
    from shared.messaging import TransactionalOutboxPublisher

    publisher = TransactionalOutboxPublisher(session)
    await publisher.publish(
        "filenest.org123.proj456.file.uploaded",
        {"file_id": "abc"},
        organization_id="org123",
        project_id="proj456",
    )
    # Then commit the session — outbox row is included in the same transaction
"""
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.session import Base


class OutboxMessage(Base):
    """
    ORM model for the `outbox_messages` table.

    Rows are inserted by `TransactionalOutboxPublisher` and consumed
    (then marked published) by the OutboxWorker process.
    """

    __tablename__ = "outbox_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject = Column(String, nullable=False)     # NATS subject for the message
    payload = Column(Text, nullable=False)        # JSON-serialised event body
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    published_at = Column(DateTime(timezone=True), nullable=True)  # None = unpublished
    organization_id = Column(String, nullable=False)
    project_id = Column(String, nullable=False)


class TransactionalOutboxPublisher:
    """
    Writes an event to the outbox table inside an existing DB transaction.

    Must be constructed with an active AsyncSession. The publisher adds the
    outbox row to the session but never flushes or commits — the service layer
    owns the transaction boundary and decides when to commit everything together.

    Args:
        session: The active SQLAlchemy async session for the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def publish(
        self,
        subject: str,
        payload: dict,
        *,
        organization_id: str,
        project_id: str,
    ) -> None:
        """
        Enqueue an event to be delivered to NATS after the current transaction commits.

        Args:
            subject:         NATS subject string, e.g. "filenest.org1.proj1.file.uploaded".
            payload:         Event body — must be JSON-serialisable.
            organization_id: Owning organisation UUID (for filtering and audit).
            project_id:      Target project UUID (for filtering and audit).
        """
        msg = OutboxMessage(
            subject=subject,
            payload=json.dumps(payload),
            organization_id=organization_id,
            project_id=project_id,
        )
        self._session.add(msg)
        # Intentionally no flush/commit — caller owns the transaction
