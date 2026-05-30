"""Dashboard API routes."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Alert, Finding, RiskScoreRecord
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/{client_id}")
async def soc_dashboard(
    client_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """SOC dashboard data."""
    enforce_tenant(user, client_id)
    alert_count = await db.scalar(
        select(func.count()).select_from(Alert).where(Alert.tenant_id == client_id, Alert.status == "open")
    )
    finding_count = await db.scalar(
        select(func.count()).select_from(Finding).where(Finding.tenant_id == client_id)
    )
    critical = await db.scalar(
        select(func.count()).select_from(Finding).where(
            Finding.tenant_id == client_id, Finding.severity == "critical"
        )
    )
    latest_risk = await db.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.tenant_id == client_id)
        .order_by(RiskScoreRecord.created_at.desc())
        .limit(1)
    )
    risk = latest_risk.scalar_one_or_none()
    return {
        "client_id": client_id,
        "kpis": {
            "active_alerts": alert_count or 0,
            "total_findings": finding_count or 0,
            "critical_findings": critical or 0,
            "risk_score": risk.composite_score if risk else 0.72,
            "risk_label": risk.business_risk_label if risk else "High",
        },
        "agents_active": 4,
        "hitl_queue_depth": 2,
    }


@router.get("/executive/{client_id}")
async def executive_dashboard(
    client_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Board / executive view."""
    enforce_tenant(user, client_id)
    return {
        "client_id": client_id,
        "risk_trend": [
            {"date": "2024-01", "score": 0.65},
            {"date": "2024-02", "score": 0.58},
            {"date": "2024-03", "score": 0.72},
        ],
        "critical_summary": [
            {"title": "Credential exposure on dark web", "severity": "critical"},
            {"title": "Unpatched CVE in crown-jewel service", "severity": "high"},
        ],
        "compliance_status": {"RBI": 0.82, "DPDP": 0.75, "PCI-DSS": 0.91},
    }
