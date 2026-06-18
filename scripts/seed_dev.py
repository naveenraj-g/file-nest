"""
scripts.seed_dev — Bootstrap a local development environment.

Creates a test organisation, project, and API key directly in the database.
Run this once after `just migrate` to get credentials for curl testing.

Usage:
    uv run python scripts/seed_dev.py

Output:
    Prints the raw API key — store it, it is shown only once.

Environment:
    Reads DATABASE_PRIMARY_URL from the .env file in the project root.
    Run `just dev` first to ensure PostgreSQL is up.
"""
import asyncio
import hashlib
import json
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on sys.path so shared/* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # type: ignore[import]

load_dotenv()

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _hash_key(raw_key: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{raw_key}".encode()).hexdigest()


async def seed() -> None:
    db_url = os.environ.get(
        "DATABASE_PRIMARY_URL",
        "postgresql+asyncpg://filenest:filenest@localhost:5434/filenest",
    )
    api_key_salt = os.environ.get("API_KEY_SALT", "dev-salt-change-in-production")

    engine = create_async_engine(db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        org_id = "org_dev_" + secrets.token_hex(4)
        project_id = str(uuid.uuid4())
        raw_key = f"fn_live_{secrets.token_urlsafe(32)}"
        key_hash = _hash_key(raw_key, api_key_salt)
        key_prefix = raw_key[:20]
        now = datetime.now(UTC)

        all_scopes = [
            "files:upload",
            "files:download",
            "files:read",
            "files:delete",
            "files:update_metadata",
            "api_keys:create",
            "api_keys:revoke",
            "projects:read",
            "projects:update",
            "audit:read",
            "compliance:manage",
        ]

        await session.execute(
            __import__("sqlalchemy").text(
                """
                INSERT INTO projects (id, organization_id, name, slug, storage_mode, is_active, created_at, updated_at)
                VALUES (:id, :org_id, :name, :slug, 'managed', true, :now, :now)
                """
            ),
            {"id": project_id, "org_id": org_id, "name": "Dev Project", "slug": "dev-project", "now": now},
        )

        key_id = str(uuid.uuid4())
        await session.execute(
            __import__("sqlalchemy").text(
                """
                INSERT INTO api_keys (id, organization_id, project_id, name, key_hash, key_prefix, scopes, is_test_mode, is_revoked, created_at)
                VALUES (:id, :org_id, :project_id, :name, :key_hash, :key_prefix, :scopes, false, false, :now)
                """
            ),
            {
                "id": key_id,
                "org_id": org_id,
                "project_id": project_id,
                "name": "Dev Key",
                "key_hash": key_hash,
                "key_prefix": key_prefix,
                "scopes": json.dumps(all_scopes),
                "now": now,
            },
        )

        await session.commit()

    await engine.dispose()

    print("\n" + "=" * 60)
    print("  FileNest dev seed complete")
    print("=" * 60)
    print(f"  Organization ID : {org_id}")
    print(f"  Project ID      : {project_id}")
    print(f"  API Key         : {raw_key}")
    print()
    print("  Save the API key — it cannot be recovered from the DB.")
    print()
    print("  Quick test:")
    print(f'    curl -H "Authorization: Bearer {raw_key}" \\')
    print("         http://localhost:8001/v1/files")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
