"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-18

Creates the three Phase 1 tables:
  - projects        — project metadata and storage configuration
  - files           — file records (metadata only; bytes live in object storage)
  - outbox_messages — transactional outbox for reliable NATS event delivery

API keys are managed entirely by the IAM (BetterAuth apiKey plugin) and
therefore do not appear in the FileNest database schema.
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_mode", sa.String(20), nullable=False, server_default="managed"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_index(
        "ix_projects_org_slug",
        "projects",
        ["organization_id", "slug"],
        unique=True,
    )

    # ── files ─────────────────────────────────────────────────────────────────
    op.create_table(
        "files",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("folder_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_organization_id", "files", ["organization_id"])
    op.create_index("ix_files_project_id", "files", ["project_id"])
    # Composite index for the primary list query (project + not deleted + newest first)
    op.create_index(
        "ix_files_project_created",
        "files",
        ["project_id", "organization_id", "created_at"],
    )

    # ── outbox_messages ───────────────────────────────────────────────────────
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # OutboxWorker polls for rows where published_at IS NULL — this index makes it fast
    op.create_index(
        "ix_outbox_unpublished",
        "outbox_messages",
        ["published_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("outbox_messages")
    op.drop_index("ix_files_project_created", "files")
    op.drop_table("files")
    op.drop_index("ix_projects_org_slug", "projects")
    op.drop_table("projects")
