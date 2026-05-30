"""Reporting synthesis API (Week 5)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.persistence import summarize_findings
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])


@router.get("/{client_id}/summary")
async def reporting_summary(
    client_id: str,
    period: str = Query("30d"),
    user: CurrentUser = Depends(require_permission("read:findings")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executive findings summary for reporting agent and UI."""
    enforce_tenant(user, client_id)
    days = 30
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            days = 30
    summary = await summarize_findings(client_id, days=days)
    return {
        "client_id": client_id,
        "period": period,
        "summary": summary,
        "executive_narrative": (
            f"Over the last {days} days, {summary['recent']} new findings were recorded "
            f"({summary['critical']} critical, {summary['high']} high). "
            f"Top contributing agents: {', '.join(summary['top_agents'][:3]) or 'none'}."
        ),
        "recommended_reports": ["Board Summary", "CISO Brief", "RBI IT Framework"],
    }
