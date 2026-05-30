"""FastAPI dependencies — auth, DB, tenant isolation."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import decode_token, has_permission, require_tenant_access
from packages.core.database import get_db
from packages.shared_types.constants import UserRole

security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Authenticated user context."""

    def __init__(self, user_id: str, email: str, role: str, tenant_id: str):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser:
    """Extract and validate JWT from Authorization header."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return CurrentUser(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            role=payload.get("role", UserRole.SOC_ANALYST),
            tenant_id=payload.get("tenant_id", ""),
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def require_permission(permission: str):
    """Dependency factory for RBAC permission check."""

    async def checker(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user

    return checker


def enforce_tenant(user: CurrentUser, requested_tenant: str) -> None:
    """Enforce tenant isolation."""
    if not require_tenant_access(user.tenant_id, requested_tenant, user.role):
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")


DbSession = Annotated[AsyncSession, Depends(get_db)]
