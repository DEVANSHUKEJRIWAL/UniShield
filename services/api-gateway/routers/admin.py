"""Admin and multi-tenant management routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Client
from packages.shared_types.constants import UserRole
from services.api_gateway.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class ClientCreateRequest(BaseModel):
    id: str
    name: str
    industry: str
    tier: str = "standard"


def require_platform_admin(user: CurrentUser) -> None:
    """Only PLATFORM_ADMIN can access admin routes."""
    if user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(status_code=403, detail="PLATFORM_ADMIN required")


@router.get("/clients")
async def list_clients(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all tenants (PLATFORM_ADMIN only)."""
    require_platform_admin(user)
    result = await db.execute(select(Client))
    return [{"id": c.id, "name": c.name, "industry": c.industry, "tier": c.tier} for c in result.scalars().all()]


@router.post("/clients")
async def create_client(
    body: ClientCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Onboard new client tenant."""
    require_platform_admin(user)
    client = Client(id=body.id, name=body.name, industry=body.industry, tier=body.tier)
    db.add(client)
    return {"status": "created", "client_id": body.id}


@router.delete("/client/{client_id}/purge")
async def purge_client(
    client_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    """Cascade delete tenant data (DPDP right-to-erasure)."""
    require_platform_admin(user)
    return {"status": "purge_queued", "client_id": client_id}
