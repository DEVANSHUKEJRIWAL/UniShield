"""Authentication routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from packages.core.database import get_db
from packages.core.models import User
from services.api_gateway.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    tenant_id: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role, "tenant_id": user.tenant_id}
    return TokenResponse(
        access_token=create_access_token(token_data, timedelta(hours=1)),
        refresh_token=create_refresh_token(token_data),
        role=user.role,
        tenant_id=user.tenant_id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Refresh access token."""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    token_data = {k: payload[k] for k in ("sub", "email", "role", "tenant_id") if k in payload}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=payload.get("role", ""),
        tenant_id=payload.get("tenant_id", ""),
    )


@router.post("/logout")
async def logout(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    """Logout — client-side token discard."""
    return {"status": "logged_out", "user_id": user.user_id}
