# Seller workspace integration

Seller data is tenant-scoped by `seller_workspaces`. A user can belong to more
than one workspace through `workspace_members`; the platform-level `users.role`
only controls whether the account is a buyer, seller, or platform admin.

## Request contract

Every seller API that reads or changes shop-owned data must receive:

```http
Authorization: Bearer <access-token>
X-Workspace-ID: <seller-workspace-id>
```

On FastAPI routes, resolve the tenant with `get_workspace_access` or enforce a
workspace role with `require_workspace_role(...)` from `app.api.deps`:

```python
from fastapi import Depends
from app.api.deps import WorkspaceAccess, require_workspace_role

_MANAGE_SHOP = require_workspace_role("owner", "manager")

async def connect_shop(
    access: WorkspaceAccess = Depends(_MANAGE_SHOP),
):
    workspace_id = access.workspace_id
```

Do not accept a body `workspace_id` as proof of access. If it is present for a
resource relation, compare it with `access.workspace_id` before using it.

## Roles

| Role | Intended permission |
|---|---|
| `owner` | Workspace settings, members, connections, all seller operations |
| `manager` | Connections and daily seller operations |
| `analyst` | Read analytics and run analysis |
| `viewer` | Read-only access |
| `platform_admin` | Support/inspection across tenants; not stored as membership |

Only owners and platform admins can add, change, or remove members. The backend
prevents the final owner from being demoted or removed.

## Frontend behavior

The active workspace is stored in the `area303_workspace` cookie. The shared API
client automatically adds `X-Workspace-ID`, so feature clients should keep using
`frontend/lib/api.ts` instead of calling `fetch` directly.

## Marketplace connector handoff

For Shopee, Lazada, or TikTok Shop integration:

1. Start OAuth/authorization with verified `WorkspaceAccess`.
2. Put a signed, short-lived state value containing `workspace_id`, `user_id`,
   platform, nonce, and expiry in the authorization URL.
3. In the callback, verify the signature, expiry, nonce, and current workspace
   membership before exchanging the code.
4. Store encrypted tokens against `(workspace_id, platform, external_shop_id)`.
5. Never store marketplace passwords.
6. Refresh tokens server-side and record connection status, last sync time, and
   the last sanitized error.
7. Every product, order, inventory, and sync-job row must carry `workspace_id`.

The current disabled “Connect Shopee” control is intentionally a handoff point;
it should only be enabled after the connector implements this contract.

After a successful OAuth code exchange, call
`marketplace_shop_service.upsert_authorized_shop(...)`. It encrypts access and
refresh tokens before ORM assignment. Use `credentials_for(...)` only inside a
server-side sync job; never serialize its return value.

## Available workspace APIs

- `POST /api/v1/workspaces/`
- `GET /api/v1/workspaces/`
- `GET /api/v1/workspaces/{workspace_id}`
- `GET /api/v1/workspaces/{workspace_id}/members`
- `POST /api/v1/workspaces/{workspace_id}/members`
- `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}`
- `GET /api/v1/workspaces/{workspace_id}/shops`
- `DELETE /api/v1/workspaces/{workspace_id}/shops/{shop_id}`

Member endpoints require `X-Workspace-ID`; path and header ids must match.
