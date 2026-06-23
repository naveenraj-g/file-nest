"""
app.services.upload_token — Business logic for upload token creation.

Creates short-lived bearer tokens that allow browser clients to call the
file upload endpoints without exposing the project's full API key.

The service runs inside the request DB transaction (the session context
manager in get_db commits on success). Expired tokens for the same project
are pruned opportunistically on each creation call.

Usage:
    from app.services.upload_token import UploadTokenService
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TenantContext
from app.models.upload_token import UploadToken
from app.repositories.upload_token import UploadTokenRepository
from app.schemas.upload_token import (
    CreateUploadTokenRequest,
    UploadTokenConstraints,
    UploadTokenResponse,
)


_DEFAULT_MAX_SIZE = 100 * 1024 * 1024   # 100 MB
_DEFAULT_MAX_FILES = 10
_DEFAULT_MIME_TYPES = ["*/*"]


class UploadTokenService:
    """Creates and validates browser upload tokens."""

    def __init__(self, session: AsyncSession, repo: UploadTokenRepository, ctx: TenantContext) -> None:
        self._session = session
        self._repo = repo
        self._ctx = ctx

    async def create(self, project_id: str, req: CreateUploadTokenRequest) -> UploadTokenResponse:
        """
        Issue a new short-lived upload token for the given project.

        Expired tokens for this project are pruned in the same transaction.
        The token value is generated with secrets.token_hex and starts with
        the fn_upload_token_ prefix so the auth layer can dispatch correctly.

        Args:
            project_id: The project that this token grants access to.
            req:        Token constraints and TTL from the request body.

        Returns:
            UploadTokenResponse with the token string, expiry, and constraints.
        """
        expires_at = datetime.now(UTC) + timedelta(seconds=req.expires_in)

        max_size = req.max_size if req.max_size is not None else _DEFAULT_MAX_SIZE
        allowed_mime_types = req.allowed_mime_types if req.allowed_mime_types is not None else _DEFAULT_MIME_TYPES
        max_files = req.max_files if req.max_files is not None else _DEFAULT_MAX_FILES

        token_value = UploadToken.generate_token()

        await self._repo.create(
            organization_id=self._ctx.organization_id,
            project_id=project_id,
            token=token_value,
            max_size=max_size,
            allowed_mime_types=allowed_mime_types,
            max_files=max_files,
            folder_id=req.folder_id,
            default_metadata=req.metadata,
            expires_at=expires_at,
        )

        # Prune stale tokens opportunistically — failure is non-fatal
        try:
            await self._repo.delete_expired(self._ctx.organization_id, project_id)
        except Exception:
            pass

        return UploadTokenResponse(
            token=token_value,
            expires_at=expires_at,
            constraints=UploadTokenConstraints(
                max_size=max_size,
                allowed_mime_types=allowed_mime_types,
                max_files=max_files,
            ),
        )
