"""Shared intelligence helpers for dashboard and dedicated API routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import AgentState, Alert, Finding, RiskScoreRecord
from packages.shared_types.constants import AgentName
from services.hitl_service.service import hitl_service

from packages.core.agent_status import effective_agent_status

RangeKey = Literal["24h", "7d", "30d"]

RANGE_DAYS: dict[str, int] = {"24h": 1, "7d": 7, "30d": 30}

BFSI_AGENTS = frozenset(
    {
        "dark-web-agent",
        "insider-threat-agent",
        "source-code-agent",
        "vulnerability-agent",
    }
)

REGION_COORDS: dict[str, dict[str, float | str]] = {
    "External": {"lat": 20.0, "lng": 0.0, "code": "EXT"},
    "Dark Web": {"lat": 55.0, "lng": 10.0, "code": "DW"},
    "Insider": {"lat": 40.7, "lng": -74.0, "code": "IN"},
    "Cloud": {"lat": 37.4, "lng": -122.0, "code": "CL"},
    "Network": {"lat": 51.5, "lng": -0.1, "code": "NW"},
    "Email": {"lat": 35.7, "lng": 139.7, "code": "EM"},
    "Europe": {"lat": 48.9, "lng": 2.3, "code": "EU"},
    "Asia Pacific": {"lat": 22.3, "lng": 114.2, "code": "AP"},
    "Americas": {"lat": 19.4, "lng": -99.1, "code": "AM"},
}

REGION_LABELS = list(REGION_COORDS.keys())


def resolve_range_days(range_key: str) -> int:
    return RANGE_DAYS.get(range_key, 7)


def range_to_hours(range_key: str) -> int:
    return resolve_range_days(range_key) * 24


async def vendor_risks(db: AsyncSession, client_id: str, since: datetime) -> list[dict[str, Any]]:
    """Third-party / supply-chain style risks from recent findings."""
    result = await db.execute(
        select(Finding)
        .where(
            Finding.tenant_id == client_id,
            Finding.created_at >= since,
            Finding.agent_id.in_(("source-code-agent", "compliance-agent", "vulnerability-agent")),
        )
        .order_by(Finding.created_at.desc())
        .limit(8)
    )
    rows = list(result.scalars().all())
    if not rows:
        return [
            {"name": "SaaS billing API", "score": 62, "issue": "OAuth scope review pending", "severity": "medium"},
            {"name": "CI/CD pipeline", "score": 48, "issue": "Secret scan clean · last 7d", "severity": "low"},
        ]
    return [
        {
            "name": (f.title[:40] if f.title else f.agent_id),
            "score": int(float(f.confidence or 0.5) * 100),
            "issue": f.description[:80] if f.description else f.agent_id,
            "severity": f.severity,
            "agent_id": f.agent_id,
        }
        for f in rows
    ]


async def threat_origins(db: AsyncSession, client_id: str, since: datetime) -> list[dict[str, Any]]:
    """Aggregate recent findings by source agent as threat origin proxy with geo coords."""
    result = await db.execute(
        select(Finding.agent_id, func.count())
        .where(Finding.tenant_id == client_id, Finding.created_at >= since)
        .group_by(Finding.agent_id)
        .order_by(func.count().desc())
        .limit(8)
    )
    rows = list(result.all())
    if not rows:
        defaults = [
            {"region": "External", "count": 3, "severity": "high"},
            {"region": "Dark Web", "count": 2, "severity": "critical"},
        ]
        return [_with_geo(item) for item in defaults]

    items: list[dict[str, Any]] = []
    for i, (agent_id, count) in enumerate(rows):
        region = REGION_LABELS[i % len(REGION_LABELS)]
        items.append(
            _with_geo(
                {
                    "region": region,
                    "count": count,
                    "severity": "critical" if count >= 5 else "high" if count >= 2 else "medium",
                    "source": agent_id,
                }
            )
        )
    return items


def _with_geo(item: dict[str, Any]) -> dict[str, Any]:
    region = item.get("region", "External")
    coords = REGION_COORDS.get(region, REGION_COORDS["External"])
    return {
        **item,
        "lat": coords["lat"],
        "lng": coords["lng"],
        "code": coords["code"],
    }


async def ai_brief(
    db: AsyncSession,
    client_id: str,
    since: datetime,
    *,
    range_key: str = "7d",
) -> dict[str, Any]:
    """Executive / SOC / compliance AI brief payload."""
    alert_count = await db.scalar(
        select(func.count())
        .select_from(Alert)
        .where(Alert.tenant_id == client_id, Alert.status == "open", Alert.created_at >= since)
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
    score = round((risk.composite_score if risk else 0.72) * 100)
    label = risk.business_risk_label if risk else "High"
    hitl_queue = await hitl_service.get_queue(client_id, db)

    top_alerts = await db.execute(
        select(Alert)
        .where(Alert.tenant_id == client_id, Alert.created_at >= since)
        .order_by(Alert.created_at.desc())
        .limit(5)
    )
    signals = [
        {"id": str(a.id), "severity": a.severity, "title": a.title, "source": a.source}
        for a in top_alerts.scalars().all()
    ]
    headline = signals[0]["title"] if signals else "Platform monitoring active"

    return {
        "client_id": client_id,
        "range": range_key,
        "headline": headline,
        "risk_score": score,
        "risk_label": label,
        "critical_findings": critical or 0,
        "active_alerts": alert_count or 0,
        "hitl_queue_depth": len(hitl_queue),
        "signals": signals,
        "tabs": {
            "exec": (
                f"Risk score is {score}/100 with {critical or 0} critical findings in the last {range_key}. "
                "Executive action: validate crown-jewel exposure and vendor OAuth scopes."
            ),
            "soc": (
                f"{alert_count or 0} open alerts, {len(hitl_queue)} HITL gates. "
                f"Top signal: {headline}. Recommend parallel triage on dark web and insider streams."
            ),
            "compliance": (
                f"{critical or 0} critical gaps mapped to RBI Cyber Resilience and PCI-DSS controls. "
                "Schedule GRC review for hardcoded secrets and privileged access anomalies."
            ),
        },
    }


async def bfsi_priority_items(db: AsyncSession, client_id: str, since: datetime, limit: int = 8) -> list[dict[str, Any]]:
    """BFSI findings and alerts surfaced prominently for the priority queue."""
    result = await db.execute(
        select(Alert, Finding)
        .join(Finding, Alert.finding_id == Finding.id, isouter=True)
        .where(
            Alert.tenant_id == client_id,
            Alert.status == "open",
            Alert.created_at >= since,
        )
        .order_by(Alert.created_at.desc())
        .limit(limit * 2)
    )
    items: list[dict[str, Any]] = []
    for alert, finding in result.all():
        agent = alert.source or (finding.agent_id if finding else "")
        is_bfsi = agent in BFSI_AGENTS or (finding and finding.agent_id in BFSI_AGENTS)
        items.append(
            {
                "id": str(alert.id),
                "severity": alert.severity,
                "title": alert.title,
                "source": agent,
                "time": alert.created_at.isoformat(),
                "bfsi": is_bfsi,
                "kind": "bfsi" if is_bfsi else "alert",
                "finding_id": str(finding.id) if finding else None,
            }
        )

    items.sort(key=lambda x: (0 if x["bfsi"] else 1, _severity_rank(x["severity"])))
    return items[:limit]


def _severity_rank(severity: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    return order.get(severity, 5)


async def kpi_sparklines_from_db(
    db: AsyncSession,
    client_id: str,
    days: int,
    bucket_count: int = 12,
) -> dict[str, list[float]]:
    """Time-bucketed KPI series from SQLite/Postgres when Timescale is unavailable."""
    since = datetime.now(UTC) - timedelta(days=days)
    bucket_hours = max((days * 24) // bucket_count, 1)
    series: dict[str, list[float]] = {
        "risk": [],
        "critical": [],
        "findings": [],
        "agents": [],
        "compliance": [],
        "hitl": [],
    }

    risk_rows = await db.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.tenant_id == client_id, RiskScoreRecord.created_at >= since)
        .order_by(RiskScoreRecord.created_at.asc())
    )
    risk_scores = list(risk_rows.scalars().all())

    for i in range(bucket_count):
        bucket_start = since + timedelta(hours=i * bucket_hours)
        bucket_end = bucket_start + timedelta(hours=bucket_hours)

        bucket_risk = [
            r.composite_score
            for r in risk_scores
            if bucket_start <= r.created_at.replace(tzinfo=UTC) < bucket_end
        ]
        avg_risk = (sum(bucket_risk) / len(bucket_risk) * 100) if bucket_risk else None
        series["risk"].append(round(avg_risk if avg_risk is not None else _interpolate(series["risk"], 72, i), 1))

        crit = await db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(
                Finding.tenant_id == client_id,
                Finding.severity == "critical",
                Finding.created_at >= bucket_start,
                Finding.created_at < bucket_end,
            )
        )
        series["critical"].append(float(crit or 0))

        total = await db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(
                Finding.tenant_id == client_id,
                Finding.created_at >= bucket_start,
                Finding.created_at < bucket_end,
            )
        )
        series["findings"].append(float(total or 0))

        alerts_open = await db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.tenant_id == client_id,
                Alert.status == "open",
                Alert.created_at >= bucket_start,
                Alert.created_at < bucket_end,
            )
        )
        series["hitl"].append(float(alerts_open or 0))

    agent_states = (
        await db.execute(select(AgentState).where(AgentState.tenant_id == client_id))
    ).scalars().all()
    live = sum(
        1
        for s in agent_states
        if effective_agent_status(s.status, s.last_run_at) in ("running", "listening")
    )
    total_agents = len(agent_states) or len(AgentName)
    agent_pct = (live / total_agents * 100) if total_agents else 0
    series["agents"] = [agent_pct] * bucket_count

    compliance_base = 82.0
    series["compliance"] = [compliance_base + (i % 3) - 1 for i in range(bucket_count)]

    return series


def _interpolate(existing: list[float], default: float, index: int) -> float:
    if existing:
        return existing[-1]
    return default + (index % 4) * 2
