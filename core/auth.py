"""JWT authentication and RBAC utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from core.config import settings
from core.constants import UserRole

ROLE_PERMISSIONS: dict[str, set[str]] = {
    UserRole.PLATFORM_ADMIN: {"*"},
    UserRole.CLIENT_ADMIN: {
        "read:*", "write:*", "hitl:*", "admin:tenant",
    },
    UserRole.CISO: {
        "read:*", "hitl:approve", "report:export", "compliance:*",
    },
    UserRole.SOC_ANALYST: {
        "read:dashboard", "read:alerts", "read:findings", "read:agents", "read:reports", "write:reports",
        "write:alerts", "hitl:decide", "read:investigation", "write:investigation",
    },
    UserRole.READONLY_BOARD: {
        "read:dashboard", "read:executive", "read:reports",
    },
    UserRole.DEVSECOPS: {
        "read:code_findings", "read:agents", "write:agents:code",
    },
    UserRole.GRC: {
        "read:compliance", "read:reports", "write:reports",
    },
}


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid4())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_expire_days)
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid4())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def has_permission(role: str, permission: str) -> bool:
    """Check if role has the given permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    if "*" in perms:
        return True
    if permission in perms:
        return True
    prefix = permission.split(":")[0]
    return f"{prefix}:*" in perms or f"read:*" in perms and permission.startswith("read:")


def require_tenant_access(token_tenant: str, requested_tenant: str, role: str) -> bool:
    """Enforce tenant isolation — PLATFORM_ADMIN bypasses."""
    if role == UserRole.PLATFORM_ADMIN:
        return True
    return token_tenant == requested_tenant
