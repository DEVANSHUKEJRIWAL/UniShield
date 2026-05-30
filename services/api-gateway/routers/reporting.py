"""Reporting synthesis API (Week 5/8)."""

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.registry import create_agent
from agents._openclaw.tools import export_pdf_report, schedule_report_job
from packages.core.database import get_db
from packages.core.models import Report
from packages.core.persistence import summarize_findings
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])

AUDIENCE_MAP = {
    "Board Summary": "board",
    "CISO Brief": "ciso",
    "Analyst Report": "analyst",
    "RBI IT Framework": "grc",
}


class GenerateReportRequest(BaseModel):
    report_type: str = "Board Summary"
    period: str = "30d"
    schedule: bool = False


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
        "recommended_reports": ["Board Summary", "CISO Brief", "Analyst Report", "RBI IT Framework"],
    }


@router.get("/{client_id}/reports")
async def list_reports(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:reports")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List generated reports for tenant."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(Report).where(Report.tenant_id == client_id).order_by(Report.created_at.desc()).limit(20)
    )
    return [
        {
            "id": str(r.id),
            "report_type": r.report_type,
            "status": r.status,
            "audience": r.audience,
            "ciso_signed": r.ciso_signed,
            "created_at": r.created_at.isoformat(),
        }
        for r in result.scalars().all()
    ]


@router.post("/{client_id}/generate")
async def generate_report(
    client_id: str,
    body: GenerateReportRequest,
    user: CurrentUser = Depends(require_permission("write:reports")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate report via reporting-agent; persist PDF-ready content."""
    enforce_tenant(user, client_id)
    days = 30
    if body.period.endswith("d"):
        try:
            days = int(body.period[:-1])
        except ValueError:
            days = 30
    summary = await summarize_findings(client_id, days=days)
    narrative = (
        f"{body.report_type} for {client_id}: {summary['recent']} recent findings, "
        f"{summary['critical']} critical. Prepared for {AUDIENCE_MAP.get(body.report_type, 'board')} audience."
    )
    pdf = await export_pdf_report(
        {"title": body.report_type, "narrative": narrative, "summary": summary},
        body.report_type,
    )
    report = Report(
        id=uuid.uuid4(),
        tenant_id=client_id,
        report_type=body.report_type,
        period=body.period,
        status="generated",
        audience=AUDIENCE_MAP.get(body.report_type, "board"),
        content={"summary": summary, "narrative": narrative, "pdf": pdf},
    )
    db.add(report)
    await db.commit()

    agent = create_agent("reporting-agent", client_id)
    await agent.on_event(
        {
            "tenant_id": client_id,
            "type": "report_request",
            "report_type": body.report_type,
            "period": body.period,
        }
    )

    if body.schedule:
        await schedule_report_job(client_id, body.report_type)

    return {
        "client_id": client_id,
        "report_id": str(report.id),
        "report_type": body.report_type,
        "status": "generated",
        "summary": summary,
        "pdf_filename": pdf.get("filename"),
        "message": f"{body.report_type} created with PDF export",
    }


@router.get("/report/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    user: CurrentUser = Depends(require_permission("read:reports")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download generated report as PDF or text."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        return Response(status_code=404, content="Report not found")
    enforce_tenant(user, report.tenant_id)
    pdf = report.content.get("pdf", {})
    raw = base64.b64decode(pdf.get("content_base64", ""))
    media = "application/pdf" if pdf.get("format") == "pdf" else "text/plain"
    return Response(content=raw, media_type=media, headers={"Content-Disposition": f'attachment; filename="{pdf.get("filename", "report.pdf")}"'})
