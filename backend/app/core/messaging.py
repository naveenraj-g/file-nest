"""
app.core.messaging — Transactional outbox for reliable NATS event publishing.

The outbox pattern guarantees at-least-once delivery even across crashes:
  1. Service writes an OutboxMessage row inside the same DB transaction as the
     business operation.
  2. Both rows commit atomically.
  3. An OutboxWorker polls unpublished rows and sends them to NATS JetStream.

Rules:
  - Never call NATS directly from a service — always use TransactionalOutboxPublisher.
  - The publisher does NOT flush or commit. The service owns the transaction.

NATS subject format: filenest.<org_id>.<project_id>.<event_type>

Usage:
    from app.core.messaging import TransactionalOutboxPublisher

    publisher = TransactionalOutboxPublisher(session)
    await publisher.publish("filenest.org1.proj1.file.uploaded", {...}, org_id="org1", project_id="proj1")
"""
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base


class OutboxMessage(Base):
    """ORM model for the outbox_messages table."""

    __tablename__ = "outbox_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    published_at = Column(DateTime(timezone=True), nullable=True)
    organization_id = Column(String, nullable=False)
    project_id = Column(String, nullable=False)


class TransactionalOutboxPublisher:
    """
    Enqueues an event into the outbox table within an existing DB transaction.

    Args:
        session: Active AsyncSession. The publisher adds the row to it but never
                 flushes or commits — the caller owns the transaction boundary.
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
        Enqueue an event for NATS delivery after the current transaction commits.

        Args:
            subject:         NATS subject, e.g. "filenest.org1.proj1.file.uploaded".
            payload:         JSON-serialisable event body.
            organization_id: Owning organisation UUID.
            project_id:      Target project UUID.
        """
        msg = OutboxMessage(
            subject=subject,
            payload=json.dumps(payload),
            organization_id=organization_id,
            project_id=project_id,
        )
        self._session.add(msg)
