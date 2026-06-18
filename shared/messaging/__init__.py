"""
shared.messaging — Transactional outbox for reliable NATS event delivery.

Re-exports the outbox model and publisher. All event publishing in service
code goes through TransactionalOutboxPublisher — never via direct NATS calls.

Usage:
    from shared.messaging import TransactionalOutboxPublisher

    publisher = TransactionalOutboxPublisher(session)
    await publisher.publish("filenest.org.proj.file.uploaded", {...},
                            organization_id=..., project_id=...)
"""
from .outbox import OutboxMessage, TransactionalOutboxPublisher

__all__ = ["OutboxMessage", "TransactionalOutboxPublisher"]
