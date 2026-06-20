"""
app.di.dependencies.file — FastAPI dependency for FileService.

Validates project_id scope on project-scoped tokens before constructing
the service. Raises 403 if the token is locked to a different project.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TenantContext, authenticate_request
from app.core.database import get_db
from app.core.messaging import TransactionalOutboxPublisher
from app.repositories.file import FileRepository
from app.repositories.file_version import FileVersionRepository
from app.repositories.project_config import ProjectConfigRepository
from app.services.file import FileService


def get_file_service(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(authenticate_request),
) -> FileService:
    """Construct a FileService, enforcing project-scoped token restrictions."""
    if ctx.project_id is not None and ctx.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PROJECT_MISMATCH",
                "message": "Token is scoped to a different project.",
            },
        )
    return FileService(
        session=session,
        repo=FileRepository(session),
        version_repo=FileVersionRepository(session),
        config_repo=ProjectConfigRepository(session),
        outbox=TransactionalOutboxPublisher(session),
        ctx=ctx,
        project_id=project_id,
    )
