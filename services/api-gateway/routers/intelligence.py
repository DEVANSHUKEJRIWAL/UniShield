"""Dedicated intelligence API routes — AI brief, vendor risk, threat geo."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.intelligence import (
    ai_brief,
    bfsi_priority_items,
    resolve_range_days,
    threat_origins,
    vendor_risks,
)
from packages.core.metrics_db import query_kpi_sparklines
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1", tags=["intelligence"])


@router.get("/ai-brief/{client_id}")
async def get_ai_brief(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Standalone AI executive brief for dashboard tabs."""
    enforce_tenant(user, client_id)
    days = resolve_range_days(range)
    since = datetime.now(UTC) - timedelta(days=days)
    return await ai_brief(db, client_id, since, range_key=range)


@router.get("/vendor-risk/{client_id}")
async def get_vendor_risk(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Third-party vendor risk scores derived from findings."""
    enforce_tenant(user, client_id)
    days = resolve_range_days(range)
    since = datetime.now(UTC) - timedelta(days=days)
    items = await vendor_risks(db, client_id, since)
    return {"client_id": client_id, "range": range, "items": items}


@router.get("/threat-geo/{client_id}")
async def get_threat_geo(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Geographic threat origin map data with lat/lng markers."""
    enforce_tenant(user, client_id)
    days = resolve_range_days(range)
    since = datetime.now(UTC) - timedelta(days=days)
    origins = await threat_origins(db, client_id, since)
    return {"client_id": client_id, "range": range, "origins": origins}


@router.get("/dashboard/{client_id}/priority-queue")
async def get_priority_queue(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Priority queue with BFSI findings surfaced first."""
    enforce_tenant(user, client_id)
    days = resolve_range_days(range)
    since = datetime.now(UTC) - timedelta(days=days)
    items = await bfsi_priority_items(db, client_id, since)
    return {"client_id": client_id, "range": range, "items": items}


@router.get("/dashboard/{client_id}/kpi-sparklines")
async def get_kpi_sparklines(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """KPI mini-chart time series (TimescaleDB with DB fallback)."""
    enforce_tenant(user, client_id)
    days = resolve_range_days(range)
    hours = days * 24
    sparklines = await query_kpi_sparklines(client_id, hours=hours, db=db, days=days)
    return {"client_id": client_id, "range": range, "sparklines": sparklines}
