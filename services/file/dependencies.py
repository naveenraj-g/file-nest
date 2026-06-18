"""
services.file.dependencies — FastAPI dependency wiring for the File Service.

Defines the `get_file_service` dependency that constructs a `FileService`
instance for each request, injecting the database session and the resolved
TenantContext from the auth middleware.

All route handlers use this dependency via `Depends(get_file_service)` — they
should never construct FileService directly, as that would bypass auth.

Usage:
    from services.file.dependencies import get_file_service
    from services.file.service import FileService
    from fastapi import Depends

    @router.get("/files")
    async def list_files(svc: FileService = Depends(get_file_service)):
        return await svc.list_files()
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import TenantContext, authenticate_request
from shared.database import get_db

from .service import FileService


async def get_file_service(
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> FileService:
    """
    Construct a FileService bound to the current request's session and tenant.

    FastAPI resolves `get_db` and `authenticate_request` first (in parallel),
    then passes both into this function. The resulting FileService is scoped
    to one request — never shared across requests.
    """
    return FileService(session=session, ctx=ctx)
