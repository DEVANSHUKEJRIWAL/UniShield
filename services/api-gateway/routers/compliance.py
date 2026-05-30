"""Compliance and reporting routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import ComplianceReport
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


class ReportGenerateRequest(BaseModel):
    framework: str
    client_id: str
    period: str = "30d"


@router.get("/{client_id}/{framework}")
async def compliance_coverage(
    client_id: str,
    framework: str,
    user: CurrentUser = Depends(require_permission("read:compliance")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Control coverage for framework."""
    enforce_tenant(user, client_id)
    return {
        "client_id": client_id,
        "framework": framework,
        "coverage_pct": 0.78,
        "controls": [
            {"id": "AC-1", "title": "Access Control Policy", "status": "implemented"},
            {"id": "AC-2", "title": "Account Management", "status": "partial"},
            {"id": "IR-4", "title": "Incident Handling", "status": "implemented"},
            {"id": "SI-4", "title": "System Monitoring", "status": "gap"},
        ],
    }


@router.post("/report/generate")
async def generate_report(
    body: ReportGenerateRequest,
    user: CurrentUser = Depends(require_permission("write:reports")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate compliance report."""
    enforce_tenant(user, body.client_id)
    report = ComplianceReport(
        id=uuid.uuid4(),
        tenant_id=body.client_id,
        framework=body.framework,
        status="draft",
        content={"period": body.period, "summary": f"Compliance report for {body.framework}"},
    )
    db.add(report)
    return {"report_id": str(report.id), "status": "generating"}


@router.get("/report/{report_id}/status")
async def report_status(
    report_id: uuid.UUID,
    user: CurrentUser = Depends(require_permission("read:compliance")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Report generation status."""
    result = await db.execute(select(ComplianceReport).where(ComplianceReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        return {"report_id": str(report_id), "status": "not_found"}
    enforce_tenant(user, report.tenant_id)
    return {
        "report_id": str(report.id),
        "status": report.status,
        "framework": report.framework,
        "ciso_signed": report.ciso_signed,
    }
