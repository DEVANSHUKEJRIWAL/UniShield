"""TimescaleDB metrics API (Week 7)."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from packages.core.metrics_db import query_metrics_trends
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/trends/{client_id}")
async def metrics_trends(
    client_id: str,
    hours: int = Query(24, ge=1, le=168),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    """Agent run and alert volume trends from TimescaleDB."""
    enforce_tenant(user, client_id)
    return await query_metrics_trends(client_id, hours=hours)
