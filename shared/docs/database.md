# shared.database — Session Management

## Purpose

Manages two async SQLAlchemy connection pools — one for the primary (read-write) PostgreSQL instance and one for the read replica. Exposes `get_db` and `get_read_db` as FastAPI dependencies, and the `Base` class that all ORM models must inherit from.

## Usage

### In a route or dependency

```python
from shared.database import get_db, get_read_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Write endpoint — use primary
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...

# Read-heavy list endpoint — use replica
async def my_list(db: AsyncSession = Depends(get_read_db)):
    ...
```

### Defining an ORM model

```python
from shared.database import Base
from sqlalchemy import Column, String

class MyModel(Base):
    __tablename__ = "my_table"
    id = Column(String, primary_key=True)
```

Every model that inherits `Base` is automatically discovered by Alembic's `env.py` for migration autogenerate.

## Session lifecycle

Each call to `get_db()` yields a session from the pool inside an `async with` block. The session:
- **commits** automatically when the route handler returns without raising.
- **rolls back** automatically if an unhandled exception propagates.

Because of this, repository methods must call `db.flush()` (not `db.commit()`) after inserts to get DB-assigned IDs — committing inside a repository would end the transaction early and break atomicity with the transactional outbox.

## Primary vs replica

| | `get_db` | `get_read_db` |
|-|----------|--------------|
| Engine | Primary | Replica (or primary if no replica configured) |
| Use for | All writes and reads that need the latest data | List/search endpoints |
| SQL echo | `True` in dev | Always `False` |

## Running migrations

```bash
just migrate          # apply all pending migrations
just migration "name" # autogenerate a new migration
just migrate-down     # roll back one step
```

Migrations live in `migrations/alembic/versions/` and target the primary database URL from `settings`.
