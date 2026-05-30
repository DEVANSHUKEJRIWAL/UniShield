"""Alert management routes."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Alert
from packages.core.pagination import paginate
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user, require_permission

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
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(require_permission("read:alerts")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Paginated alert list with filters."""
    enforce_tenant(user, client_id)
    q = select(Alert).where(Alert.tenant_id == client_id)
    count_q = select(func.count()).select_from(Alert).where(Alert.tenant_id == client_id)
    if severity:
        q = q.where(Alert.severity == severity)
        count_q = count_q.where(Alert.severity == severity)
    if status:
        q = q.where(Alert.status == status)
        count_q = count_q.where(Alert.status == status)
    total = await db.scalar(count_q) or 0
    meta = paginate(total, page, page_size)
    result = await db.execute(
        q.order_by(Alert.created_at.desc()).offset(meta["offset"]).limit(meta["page_size"])
    )
    items = [
        {
            "id": str(a.id),
            "title": a.title,
            "severity": a.severity,
            "status": a.status,
            "assigned_to": a.assigned_to,
            "source": a.source,
            "finding_id": str(a.finding_id) if a.finding_id else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]
    return {**meta, "total": total, "items": items}


@router.put("/{alert_id}/assign")
async def assign_alert(
    alert_id: uuid.UUID,
    body: AssignRequest,
    user: CurrentUser = Depends(require_permission("write:alerts")),
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
    user: CurrentUser = Depends(require_permission("write:alerts")),
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
