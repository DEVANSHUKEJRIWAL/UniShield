"""Alert management routes."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Alert
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AssignRequest(BaseModel):
    assigned_to: str


class StatusRequest(BaseModel):
    status: str


@router.get("/{client_id}")
async def list_alerts(
    client_id: str,
    severity: str | None = None,
    status: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Alert list with filters."""
    enforce_tenant(user, client_id)
    q = select(Alert).where(Alert.tenant_id == client_id)
    if severity:
        q = q.where(Alert.severity == severity)
    if status:
        q = q.where(Alert.status == status)
    result = await db.execute(q.order_by(Alert.created_at.desc()).limit(100))
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "severity": a.severity,
            "status": a.status,
            "assigned_to": a.assigned_to,
            "source": a.source,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.put("/{alert_id}/assign")
async def assign_alert(
    alert_id: uuid.UUID,
    body: AssignRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Assign alert to analyst."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    enforce_tenant(user, alert.tenant_id)
    alert.assigned_to = body.assigned_to
    alert.updated_at = datetime.now(UTC)
    return {"status": "assigned", "alert_id": str(alert_id)}


@router.put("/{alert_id}/status")
async def update_alert_status(
    alert_id: uuid.UUID,
    body: StatusRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Update alert status."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    enforce_tenant(user, alert.tenant_id)
    alert.status = body.status
    alert.updated_at = datetime.now(UTC)
    return {"status": "updated", "alert_id": str(alert_id)}
