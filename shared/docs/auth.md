# shared.auth — Authentication & Authorisation

## Purpose

Provides the three building blocks every service route needs:

1. **`authenticate_request`** — FastAPI dependency that reads the `Authorization` header, verifies the token, and stores the result in a ContextVar.
2. **`TenantContext`** — Immutable dataclass holding the resolved caller identity (org, project, scopes).
3. **`require_scope`** — Inline scope check that raises HTTP 403 if the caller lacks a required permission.

## Token formats

| Prefix | Type | Verified by |
|--------|------|-------------|
| `fn_live_…` | Live API key | `verify_api_key` (identity service, Phase 1) |
| `fn_test_…` | Test API key | `verify_api_key` — sets `is_test_mode=True` |
| `fn_sa_…` | Service account key | `verify_api_key` (Phase 2) |
| `fn_upload_token_…` | Short-lived browser token | `verify_api_key` (Phase 2) |
| JWT (no prefix) | User session token from IAM | `verify_jwt` |

## Usage

### Protect a route

```python
from shared.auth import authenticate_request, require_scope, TenantContext
from fastapi import Depends

@router.post("/files/upload")
async def upload(ctx: TenantContext = Depends(authenticate_request)):
    require_scope("files:upload")
    # ctx.organization_id, ctx.project_id, ctx.actor_id are now available
```

### Read context without injecting it

```python
from shared.auth import get_tenant_context

ctx = get_tenant_context()   # reads the ContextVar; safe inside any async code
                              # that runs after authenticate_request
```

## TenantContext fields

| Field | Type | Description |
|-------|------|-------------|
| `organization_id` | str | Owning organisation UUID |
| `project_id` | str | Target project UUID |
| `actor_id` | str | User ID or API key ID (for audit logs) |
| `scopes` | frozenset[str] | Granted permission scopes |
| `is_test_mode` | bool | True when using a `fn_test_` key |

## Available scopes

```
files:upload            files:download          files:read
files:delete            files:update_metadata
api_keys:create         api_keys:revoke
projects:read           projects:update
audit:read              compliance:manage
```

## Patterns & rules

- **Never** add `organization_id` or `project_id` as query/path parameters for auth — always read them from `TenantContext`.
- **Never** call `verify_jwt` or `verify_api_key` directly from a route — go through `authenticate_request`.
- Repository queries must always use `ctx.organization_id` and `ctx.project_id` as filters, never trust values from request bodies.
