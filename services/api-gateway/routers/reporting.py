"""Reporting synthesis API (Week 5)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agents.registry import create_agent
from packages.core.database import get_db
from packages.core.persistence import summarize_findings
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])


class GenerateReportRequest(BaseModel):
    report_type: str = "Board Summary"
    period: str = "30d"


@router.get("/{client_id}/summary")
async def reporting_summary(
    client_id: str,
    period: str = Query("30d"),
    user: CurrentUser = Depends(require_permission("read:reports")),
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


@router.post("/{client_id}/generate")
async def generate_report(
    client_id: str,
    body: GenerateReportRequest,
    user: CurrentUser = Depends(require_permission("write:reports")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate report via reporting-agent structured handler."""
    enforce_tenant(user, client_id)
    agent = create_agent("reporting-agent", client_id)
    await agent.on_event(
        {
            "tenant_id": client_id,
            "input": {
                "type": "report_request",
                "report_type": body.report_type,
                "period": body.period,
            },
        }
    )
    summary = await summarize_findings(client_id, days=30)
    return {
        "client_id": client_id,
        "report_type": body.report_type,
        "status": "generated",
        "summary": summary,
        "message": f"{body.report_type} draft created by reporting-agent",
    }
