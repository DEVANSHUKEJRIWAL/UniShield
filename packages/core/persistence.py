"""Persist agent outputs, run logs, alerts, and risk scores."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from packages.core.database import SessionLocal
from packages.core.models import AgentRunLog, AgentState, Alert, CVERecord, Finding, InsiderBaseline, RiskScoreRecord
from packages.core.schemas import AgentFinding
from services.risk_engine.service import risk_engine


async def persist_finding(finding: AgentFinding | dict[str, Any]) -> uuid.UUID:
    """Write finding to DB, score risk, and create alert when severity warrants."""
    data = finding.model_dump(mode="json") if isinstance(finding, AgentFinding) else finding
    fid = uuid.UUID(data.get("finding_id")) if _valid_uuid(data.get("finding_id")) else uuid.uuid4()
    tenant_id = data["tenant_id"]
    severity = data.get("severity", "medium")

    async with SessionLocal() as db:
        record = Finding(
            id=fid,
            tenant_id=tenant_id,
            agent_id=data.get("agent_id", "unknown"),
            type=data.get("type", "analysis"),
            severity=severity,
            confidence=float(data.get("confidence", 0.0)),
            title=data.get("title", "Agent finding")[:512],
            description=data.get("description", ""),
            reasoning_summary=data.get("reasoning_summary", ""),
            evidence_references=data.get("evidence_references", []),
            mitre_ttps=data.get("mitre_ttps_matched", data.get("mitre_ttps", [])),
            contributing_agents=data.get("contributing_agents", []),
            raw_output=data,
        )
        db.add(record)

        if severity in ("critical", "high"):
            db.add(
                Alert(
                    tenant_id=tenant_id,
                    finding_id=fid,
                    severity=severity,
                    title=data.get("title", "Agent finding")[:512],
                    source=data.get("agent_id", "agent"),
                    status="open",
                )
            )

        score = risk_engine.score_finding({**data, "finding_id": str(fid), "id": str(fid)})
        db.add(
            RiskScoreRecord(
                finding_id=str(fid),
                tenant_id=tenant_id,
                composite_score=score.composite_score,
                business_risk_label=score.business_risk_label,
                dimensions={
                    "exploitability": score.exploitability,
                    "cvss_base": score.cvss_base,
                    "detection_confidence": score.detection_confidence,
                },
                regulatory_exposure=score.regulatory_exposure,
                recommended_actions=score.recommended_actions,
            )
        )
        await db.commit()

    try:
        from services.search.service import search_service

        await search_service.index_finding({**data, "id": str(fid)})
    except Exception:
        pass

    try:
        from packages.core.kg_sync import sync_finding_to_kg

        await sync_finding_to_kg({**data, "finding_id": str(fid), "id": str(fid)})
    except Exception:
        pass

    if severity in ("critical", "high"):
        try:
            from packages.core.metrics_db import record_alert_volume

            await record_alert_volume(tenant_id, severity)
        except Exception:
            pass

    return fid


async def update_agent_presence(
    agent_name: str,
    tenant_id: str,
    *,
    status: str = "listening",
) -> None:
    """Mark agent worker online (listening) or offline (idle) for dashboard health."""
    now = datetime.now(UTC)
    async with SessionLocal() as db:
        result = await db.execute(
            select(AgentState).where(
                AgentState.agent_name == agent_name,
                AgentState.tenant_id == tenant_id,
            )
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = AgentState(agent_name=agent_name, tenant_id=tenant_id)
            db.add(state)
        if state.status != "running":
            state.status = status
        state.last_run_at = now
        state.health = "healthy"
        await db.commit()


async def log_agent_run(
    agent_name: str,
    tenant_id: str,
    *,
    task_id: str | None = None,
    status: str = "completed",
    input_data: dict[str, Any] | None = None,
    output: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> None:
    """Append agent run history and update agent state."""
    now = datetime.now(UTC)
    async with SessionLocal() as db:
        db.add(
            AgentRunLog(
                agent_name=agent_name,
                tenant_id=tenant_id,
                task_id=task_id,
                status=status,
                input_data=input_data or {},
                output=output,
                tool_calls=tool_calls or [],
                error=error,
                finished_at=now,
            )
        )
        result = await db.execute(
            select(AgentState).where(
                AgentState.agent_name == agent_name,
                AgentState.tenant_id == tenant_id,
            )
        )
        state = result.scalar_one_or_none()
        if state is None:
            state = AgentState(agent_name=agent_name, tenant_id=tenant_id)
            db.add(state)
        state.status = (
            "running"
            if status == "started"
            else "error"
            if status == "error"
            else "listening"
            if status == "completed"
            else "idle"
        )
        state.last_run_at = now
        state.last_output = (output or error or "")[:4000]
        if tool_calls:
            log = list(state.tool_call_log or [])
            log.extend(tool_calls[-10:])
            state.tool_call_log = log[-50:]
        state.health = "healthy" if status != "error" else "degraded"
        await db.commit()

    try:
        from packages.core.kg_sync import sync_agent_run_to_kg
        from packages.core.metrics_db import record_agent_run

        await sync_agent_run_to_kg(agent_name, tenant_id, status)
        await record_agent_run(tenant_id, agent_name, status)
    except Exception:
        pass


async def upsert_cve_records(cves: list[dict[str, Any]]) -> int:
    """Store normalised CVE records from NVD poller."""
    count = 0
    async with SessionLocal() as db:
        for item in cves:
            cve_id = item.get("cve_id")
            if not cve_id:
                continue
            existing = await db.execute(select(CVERecord).where(CVERecord.cve_id == cve_id))
            row = existing.scalar_one_or_none()
            if row is None:
                db.add(
                    CVERecord(
                        cve_id=cve_id,
                        cvss_score=float(item.get("cvss_score", 0)),
                        severity=item.get("severity", "medium"),
                        description=item.get("description", "")[:2000],
                        published=item.get("published"),
                        raw=item,
                    )
                )
                count += 1
            else:
                row.cvss_score = float(item.get("cvss_score", row.cvss_score))
                row.severity = item.get("severity", row.severity)
                row.description = item.get("description", row.description)[:2000]
                row.raw = item
        await db.commit()
    return count


async def upsert_insider_baseline(tenant_id: str, user_id: str, baseline: dict[str, Any], peer_group: str = "default") -> None:
    """Store or update UEBA baseline for a user."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(InsiderBaseline).where(
                InsiderBaseline.tenant_id == tenant_id,
                InsiderBaseline.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            db.add(
                InsiderBaseline(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    peer_group=peer_group,
                    baseline=baseline,
                )
            )
        else:
            row.baseline = baseline
            row.peer_group = peer_group
            row.updated_at = datetime.now(UTC)
        await db.commit()


async def get_insider_baseline(tenant_id: str, user_id: str) -> dict[str, Any] | None:
    """Load persisted UEBA baseline."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(InsiderBaseline).where(
                InsiderBaseline.tenant_id == tenant_id,
                InsiderBaseline.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "user_id": row.user_id,
            "tenant_id": row.tenant_id,
            "peer_group": row.peer_group,
            **row.baseline,
        }


def _valid_uuid(value: Any) -> bool:
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


async def summarize_findings(tenant_id: str, days: int = 30) -> dict[str, Any]:
    """Aggregate findings counts for reporting (Week 5)."""
    from datetime import timedelta

    from sqlalchemy import func

    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with SessionLocal() as db:
        total = await db.scalar(
            select(func.count()).select_from(Finding).where(Finding.tenant_id == tenant_id)
        )
        recent = await db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(Finding.tenant_id == tenant_id, Finding.created_at >= cutoff)
        )
        by_severity: dict[str, int] = {}
        for sev in ("critical", "high", "medium", "low", "info"):
            by_severity[sev] = (
                await db.scalar(
                    select(func.count())
                    .select_from(Finding)
                    .where(Finding.tenant_id == tenant_id, Finding.severity == sev)
                )
                or 0
            )
        agent_rows = await db.execute(
            select(Finding.agent_id, func.count())
            .where(Finding.tenant_id == tenant_id)
            .group_by(Finding.agent_id)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_agents = [row[0] for row in agent_rows.all()]
    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "total": total or 0,
        "recent": recent or 0,
        "critical": by_severity.get("critical", 0),
        "high": by_severity.get("high", 0),
        "medium": by_severity.get("medium", 0),
        "low": by_severity.get("low", 0),
        "info": by_severity.get("info", 0),
        "top_agents": top_agents,
    }

