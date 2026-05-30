"""Compliance and reporting routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.compliance.coverage import compute_coverage
from packages.core.database import get_db
from packages.core.models import ComplianceReport, Finding
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


class ReportGenerateRequest(BaseModel):
    framework: str
    client_id: str
    period: str = "30d"


async def _findings_for_tenant(db: AsyncSession, client_id: str) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Finding).where(Finding.tenant_id == client_id).order_by(Finding.created_at.desc()).limit(100)
    )
    return [
        {
            "severity": f.severity,
            "mitre_ttps": f.mitre_ttps,
            "title": f.title,
        }
        for f in result.scalars().all()
    ]


@router.get("/{client_id}/{framework}")
async def compliance_coverage(
    client_id: str,
    framework: str,
    user: CurrentUser = Depends(require_permission("read:compliance")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Control coverage derived from findings and framework catalog."""
    enforce_tenant(user, client_id)
    findings = await _findings_for_tenant(db, client_id)
    coverage = compute_coverage(framework, findings)
    coverage["client_id"] = client_id
    return coverage


@router.get("/{client_id}/{framework}/attck")
async def attck_mapping(
    client_id: str,
    framework: str,
    user: CurrentUser = Depends(require_permission("read:compliance")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """ATT&CK technique mapping for compliance heatmap."""
    enforce_tenant(user, client_id)
    findings = await _findings_for_tenant(db, client_id)
    coverage = compute_coverage(framework, findings)
    return {
        "client_id": client_id,
        "framework": framework,
        "techniques": coverage.get("attck_techniques", []),
        "controls": coverage.get("controls", []),
    }


@router.post("/report/generate")
async def generate_report(
    body: ReportGenerateRequest,
    user: CurrentUser = Depends(require_permission("write:reports")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate compliance report."""
    enforce_tenant(user, body.client_id)
    findings = await _findings_for_tenant(db, body.client_id)
    coverage = compute_coverage(body.framework, findings)
    report = ComplianceReport(
        id=uuid.uuid4(),
        tenant_id=body.client_id,
        framework=body.framework,
        status="generated",
        content={"period": body.period, "coverage": coverage},
    )
    db.add(report)
    await db.commit()
    return {"report_id": str(report.id), "status": "generated", "coverage_pct": coverage.get("coverage_pct")}


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
        "content": report.content,
    }
