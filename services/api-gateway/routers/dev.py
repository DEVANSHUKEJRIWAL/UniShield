"""Dev diagnostics routes — local troubleshooting only."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.api_keys import anthropic_live_enabled
from packages.core.auth import verify_password
from packages.core.config import settings
from packages.core.database import SessionLocal
from packages.core.integrations import integration_status, week1_readiness
from packages.core.readiness import week3_6_readiness
from packages.core.models import User
from packages.core.seed import ensure_demo_users

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


@router.get("/status")
async def dev_status() -> dict[str, Any]:
    """Show database mode, login readiness, and Week 1 integration status."""
    async with SessionLocal() as db:
        user_count = await db.scalar(select(func.count()).select_from(User)) or 0
        result = await db.execute(select(User).where(User.email == "analyst@meridian.com"))
        analyst = result.scalar_one_or_none()
        password_ok = (
            analyst is not None and verify_password("analyst123", analyst.password_hash)
        )

    return {
        "database": "sqlite" if settings.uses_sqlite else "postgresql",
        "database_uri": settings.database_uri.split("@")[-1] if "@" in settings.database_uri else settings.database_uri,
        "sqlite_path": settings.sqlite_path,
        "user_count": user_count,
        "analyst_exists": analyst is not None,
        "analyst_password_ok": password_ok,
        "login_should_work": analyst is not None and password_ok,
        "week1": week1_readiness(),
        "week3_6": week3_6_readiness(),
        "integrations": integration_status(),
        "hint": _dev_hint(analyst is not None, password_ok),
    }


def _dev_hint(analyst_exists: bool, password_ok: bool) -> str:
    if not password_ok:
        return "Run: curl -X POST http://localhost:8000/api/v1/dev/fix-login"
    if not anthropic_live_enabled():
        anthropic = integration_status().get("anthropic", {})
        if anthropic.get("configured") and not anthropic.get("key_format_valid"):
            return (
                "ANTHROPIC_API_KEY is set but invalid format (expected sk-ant-...). "
                "Agents use mock findings until fixed. Login: analyst@meridian.com / analyst123"
            )
        if anthropic.get("configured") and not anthropic.get("live_enabled"):
            return (
                "ANTHROPIC_API_KEY looks like a placeholder or was rejected by Anthropic. "
                "Agents fall back to mock findings. Login: analyst@meridian.com / analyst123"
            )
    return "Login with analyst@meridian.com / analyst123"


@router.post("/fix-login")
async def fix_login() -> dict[str, Any]:
    """Reset demo user passwords (local dev only)."""
    async with SessionLocal() as db:
        updated = await ensure_demo_users(db)
        result = await db.execute(select(User).where(User.email == "analyst@meridian.com"))
        analyst = result.scalar_one_or_none()
        ok = analyst is not None and verify_password("analyst123", analyst.password_hash)
    return {
        "status": "fixed" if ok else "failed",
        "users_updated": updated,
        "analyst_password_ok": ok,
        "try": 'curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d \'{"email":"analyst@meridian.com","password":"analyst123"}\'',
    }
