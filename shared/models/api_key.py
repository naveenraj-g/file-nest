"""
shared.models.api_key — SQLAlchemy ORM model for the `api_keys` table.

API keys are the primary authentication mechanism for server-to-server calls
against the FileNest backend. They are scoped to a specific project and carry
an explicit list of permission scopes.

Key security invariants:
  - The raw key is shown exactly once (at creation) and is never stored.
  - Only a SHA-256 hash of `{salt}:{raw_key}` is persisted in this table.
  - The first 20 characters of the raw key are stored as `key_prefix` for display.
  - Revoked keys are not deleted — their `is_revoked` flag is set instead so that
    audit logs referencing `key_id` remain meaningful.

Usage:
    from shared.models.api_key import ApiKey
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String

from shared.database import Base


class ApiKey(Base):
    """
    ORM model for the `api_keys` table.

    Managed via the Identity Service (`services/identity/`). The `key_hash`
    column is the index used by `verify_api_key` on every authenticated request.

    Attributes:
        id:              UUID primary key.
        organization_id: Owning organisation UUID.
        project_id:      Owning project UUID — all file operations use this scope.
        name:            Human-readable label (e.g. "Production SDK key").
        key_hash:        SHA-256("{salt}:{raw_key}") — used for verification.
        key_prefix:      First 20 chars of raw key — displayed in the console.
        scopes:          JSON list of granted permission strings.
        is_test_mode:    True when the raw key starts with "fn_test_".
        is_revoked:      True after the key has been revoked; never deleted.
        last_used_at:    Updated on each successful verification (best-effort).
        expires_at:      Optional expiry; None means the key never expires.
        created_at:      Creation timestamp.
    """

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False, index=True)
    project_id = Column(String, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)
    key_prefix = Column(String(30), nullable=False)
    scopes = Column(JSON, nullable=False)
    is_test_mode = Column(Boolean, nullable=False, default=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
