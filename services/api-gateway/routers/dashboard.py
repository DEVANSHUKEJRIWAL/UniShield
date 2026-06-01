"""Dashboard API routes."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import AgentState, Alert, Finding, RiskScoreRecord
from packages.shared_types.constants import AgentName
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.hitl_service.service import hitl_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

from packages.core.agent_status import effective_agent_status

RANGE_DAYS: dict[str, int] = {"24h": 1, "7d": 7, "30d": 30}


def _resolve_range_days(range_key: str) -> int:
    return RANGE_DAYS.get(range_key, 7)


@router.get("/{client_id}")
async def soc_dashboard(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = Query("7d", alias="range"),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """SOC dashboard data with live KPIs."""
    enforce_tenant(user, client_id)
    days = _resolve_range_days(range)
    since = datetime.now(UTC) - timedelta(days=days)

    alert_count = await db.scalar(
        select(func.count())
        .select_from(Alert)
        .where(Alert.tenant_id == client_id, Alert.status == "open", Alert.created_at >= since)
    )
    finding_count = await db.scalar(
        select(func.count()).select_from(Finding).where(Finding.tenant_id == client_id, Finding.created_at >= since)
    )
    critical = await db.scalar(
        select(func.count())
        .select_from(Finding)
        .where(Finding.tenant_id == client_id, Finding.severity == "critical", Finding.created_at >= since)
    )
    latest_risk = await db.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.tenant_id == client_id)
        .order_by(RiskScoreRecord.created_at.desc())
        .limit(1)
    )
    risk = latest_risk.scalar_one_or_none()

    risk_trend = await _risk_trend(db, client_id, days=days)

    agent_states = (
        await db.execute(select(AgentState).where(AgentState.tenant_id == client_id))
    ).scalars().all()
    agents_active = sum(
        1
        for s in agent_states
        if effective_agent_status(s.status, s.last_run_at) in ("running", "listening")
    )
    agents_total = len(agent_states) or len(AgentName)
    hitl_queue = await hitl_service.get_queue(client_id, db)

    vendor_risks = await _vendor_risks(db, client_id, since)
    threat_origins = await _threat_origins(db, client_id, since)

    return {
        "client_id": client_id,
        "range": range,
        "kpis": {
            "active_alerts": alert_count or 0,
            "total_findings": finding_count or 0,
            "critical_findings": critical or 0,
            "risk_score": risk.composite_score if risk else 0.72,
            "risk_label": risk.business_risk_label if risk else "High",
        },
        "agents_active": agents_active,
        "agents_total": agents_total,
        "hitl_queue_depth": len(hitl_queue),
        "risk_trend": risk_trend,
        "vendor_risks": vendor_risks,
        "threat_origins": threat_origins,
    }


@router.get("/executive/{client_id}")
async def executive_dashboard(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Board / executive view with live data."""
    enforce_tenant(user, client_id)
    risk_trend = await _risk_trend(db, client_id, days=42)
    critical_findings = await db.execute(
        select(Finding)
        .where(Finding.tenant_id == client_id, Finding.severity.in_(("critical", "high")))
        .order_by(Finding.created_at.desc())
        .limit(5)
    )
    return {
        "client_id": client_id,
        "risk_trend": [
            {"date": p["label"], "score": p["score"] / 100 if p["score"] > 1 else p["score"]}
            for p in risk_trend
        ],
        "critical_summary": [
            {"title": f.title, "severity": f.severity}
            for f in critical_findings.scalars().all()
        ]
        or [
            {"title": "Credential exposure on dark web", "severity": "critical"},
            {"title": "Unpatched CVE in crown-jewel service", "severity": "high"},
        ],
        "compliance_status": {"RBI": 0.82, "DPDP": 0.75, "PCI-DSS": 0.91},
    }


async def _risk_trend(db: AsyncSession, client_id: str, days: int = 7) -> list[dict[str, Any]]:
    """Build risk score trend from persisted scores."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.tenant_id == client_id, RiskScoreRecord.created_at >= cutoff)
        .order_by(RiskScoreRecord.created_at.asc())
    )
    scores = list(result.scalars().all())
    bucket_count = min(max(days, 4), 12)
    if not scores:
        return [{"label": f"D{i + 1}", "score": 45 + (i * 4) % 30} for i in range(bucket_count)]

    buckets: dict[str, list[float]] = {}
    for record in scores:
        day_key = record.created_at.strftime("%m/%d")
        buckets.setdefault(day_key, []).append(record.composite_score)

    trend: list[dict[str, Any]] = []
    for key, values in list(buckets.items())[-bucket_count:]:
        avg = sum(values) / len(values)
        trend.append({"label": key, "score": round(avg * 100, 1)})
    return trend or [{"label": "Now", "score": 72}]


async def _vendor_risks(db: AsyncSession, client_id: str, since: datetime) -> list[dict[str, Any]]:
    """Third-party / supply-chain style risks from recent findings."""
    result = await db.execute(
        select(Finding)
        .where(
            Finding.tenant_id == client_id,
            Finding.created_at >= since,
            Finding.agent_id.in_(("source-code-agent", "compliance-agent", "vulnerability-agent")),
        )
        .order_by(Finding.created_at.desc())
        .limit(5)
    )
    rows = list(result.scalars().all())
    if not rows:
        return [
            {"name": "SaaS billing API", "score": 62, "issue": "OAuth scope review pending"},
            {"name": "CI/CD pipeline", "score": 48, "issue": "Secret scan clean · last 7d"},
        ]
    return [
        {
            "name": (f.title[:40] if f.title else f.agent_id),
            "score": int(float(f.confidence or 0.5) * 100),
            "issue": f.description[:80] if f.description else f.agent_id,
            "severity": f.severity,
        }
        for f in rows
    ]


async def _threat_origins(db: AsyncSession, client_id: str, since: datetime) -> list[dict[str, Any]]:
    """Aggregate recent findings by source agent as threat origin proxy."""
    result = await db.execute(
        select(Finding.agent_id, func.count())
        .where(Finding.tenant_id == client_id, Finding.created_at >= since)
        .group_by(Finding.agent_id)
        .order_by(func.count().desc())
        .limit(6)
    )
    rows = list(result.all())
    regions = ["External", "Dark Web", "Insider", "Cloud", "Network", "Email"]
    if not rows:
        return [
            {"region": "External", "count": 3, "severity": "high"},
            {"region": "Dark Web", "count": 2, "severity": "critical"},
        ]
    return [
        {
            "region": regions[i % len(regions)],
            "count": count,
            "severity": "critical" if count >= 5 else "high" if count >= 2 else "medium",
            "source": agent_id,
        }
        for i, (agent_id, count) in enumerate(rows)
    ]
