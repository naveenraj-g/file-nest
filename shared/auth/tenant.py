"""
shared.auth.tenant — Immutable tenant context and async-safe ContextVar storage.

`TenantContext` is populated once per request by `authenticate_request` and
stored in a ContextVar so that any downstream code (service, repository,
logging middleware) can read the current tenant without passing it through
every function call.

Design constraints:
  - The dataclass is frozen (immutable) — downstream code must never mutate it.
  - The ContextVar is per-async-task, so concurrent requests never share state.
  - `require_auth()` raises RuntimeError (not HTTP 401) if called before
    `authenticate_request` has set the context — this is a programmer error,
    not a client error.

Usage:
    from shared.auth.tenant import get_tenant_context

    ctx = get_tenant_context()
    log.info("event", org_id=ctx.organization_id, project_id=ctx.project_id)
"""
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable snapshot of who is making the current request and what they can do.

    Populated from either a JWT (user session via IAM) or a hashed API key
    (server-to-server). Every repository query must filter by `organization_id`
    and `project_id` taken from this object — never from request parameters.

    Attributes:
        organization_id: The owning organisation's UUID.
        project_id:      The target project's UUID.
        actor_id:        User ID or API key ID — used in audit log entries.
        scopes:          Frozenset of granted permission scopes (e.g. "files:upload").
        is_test_mode:    True when the request uses a `fn_test_` prefixed API key.
    """

    organization_id: str
    project_id: str
    actor_id: str
    scopes: frozenset[str]
    is_test_mode: bool = False


_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_ctx", default=None)


def set_tenant_context(ctx: TenantContext) -> None:
    """Store the resolved tenant context for the current async task."""
    _tenant_ctx.set(ctx)


def get_tenant_context() -> TenantContext:
    """
    Retrieve the tenant context set by `authenticate_request`.

    Raises:
        RuntimeError: If called before authenticate_request has run (programmer error).
    """
    ctx = _tenant_ctx.get()
    if ctx is None:
        raise RuntimeError("No tenant context — authenticate_request must run first")
    return ctx


def require_auth() -> TenantContext:
    """Alias for get_tenant_context(); use in service code for readability."""
    return get_tenant_context()
