"""Workflow orchestrator BFF — proxies unishield/ API through api-gateway."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.api_gateway.orchestrator_client import OrchestratorClient, OrchestratorUnavailable, orchestrator_client

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_DEFAULT_WORKFLOW_AGENTS = ("scr", "cma", "reporting")
_TREND_SLOTS = 6


def _normalize_agent_key(agent_id: str) -> str:
    return agent_id.removeprefix("unishield-")


def _agent_row_status(raw: str) -> str:
    if raw == "RUNNING":
        return "running"
    if raw == "FAILED":
        return "error"
    if raw == "DONE":
        return "listening"
    return "idle"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _risk_label_from_score(score: int) -> str:
    if score >= 70:
        return "Elevated"
    if score >= 50:
        return "Moderate"
    return "Low"


def _pad_series(values: list[int | float], size: int = _TREND_SLOTS) -> list[int]:
    if not values:
        return [0] * size
    padded = values[-size:]
    if len(padded) < size:
        pad = [padded[0]] * (size - len(padded))
        padded = pad + padded
    return [int(round(v)) for v in padded]


def _build_workflow_agents(workflows: list[dict[str, Any]]) -> list[dict[str, str]]:
    status_by_agent: dict[str, str] = {}
    for wf in workflows:
        if wf.get("status") not in ("RUNNING", "PAUSED"):
            continue
        for agent_id, raw in (wf.get("agent_states") or {}).items():
            key = _normalize_agent_key(agent_id)
            mapped = _agent_row_status(str(raw))
            prev = status_by_agent.get(key)
            if prev is None or mapped == "running" or (mapped == "error" and prev != "running"):
                status_by_agent[key] = mapped

    if not status_by_agent:
        return [{"name": name, "status": "idle"} for name in _DEFAULT_WORKFLOW_AGENTS]

    return [{"name": name, "status": status_by_agent.get(name, "idle")} for name in sorted(status_by_agent)]


async def _build_scr_series(
    workflows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (completed_scr_points, priority_queue, scr_snapshots) from workflow history."""
    completed_points: list[dict[str, Any]] = []
    priority_queue: list[dict[str, Any]] = []
    scr_snapshots: list[dict[str, Any]] = []

    for wf in workflows:
        if wf.get("status") != "COMPLETED":
            continue
        wf_id = wf.get("workflow_id")
        if not wf_id:
            continue
        try:
            output = await orchestrator_client.get_output(wf_id)
        except OrchestratorUnavailable:
            continue
        if not output:
            continue
        scr = (output.get("snapshot") or {}).get("scr") or {}
        scr_snapshots.append(scr)
        risk = int(scr.get("risk_score") or 0)
        findings = scr.get("top_findings") or []
        critical = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
        completed_points.append(
            {
                "workflow_id": wf_id,
                "completed_at": wf.get("completed_at") or wf.get("started_at"),
                "risk_score": risk,
                "total_findings": len(findings),
                "critical_findings": critical,
            }
        )
        for finding in findings:
            sev = str(finding.get("severity", "medium")).lower()
            priority_queue.append(
                {
                    "id": finding.get("finding_id") or f"{wf_id}-{len(priority_queue)}",
                    "severity": sev,
                    "title": finding.get("category") or finding.get("file_path") or "SCR finding",
                    "source": "unishield-scr",
                    "time": wf.get("completed_at") or wf.get("started_at"),
                    "workflow_id": wf_id,
                    "file_path": finding.get("file_path"),
                }
            )

    completed_points.sort(key=lambda p: _parse_ts(p.get("completed_at")) or datetime.min)
    priority_queue.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"], 4))
    return completed_points, priority_queue, scr_snapshots


def _build_trend_and_sparklines(
    scr_points: list[dict[str, Any]],
    *,
    compliance_series: list[int] | None = None,
    hitl_series: list[int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    risk_series = [int(p.get("risk_score") or 0) for p in scr_points]
    critical_series = [int(p.get("critical_findings") or 0) for p in scr_points]
    findings_series = [int(p.get("total_findings") or 0) for p in scr_points]
    padded_risk = _pad_series(risk_series)
    trend = [{"label": f"W{i + 1}", "score": padded_risk[i]} for i in range(_TREND_SLOTS)]

    sparklines = {
        "risk": _pad_series(risk_series),
        "critical": _pad_series(critical_series),
        "findings": _pad_series(findings_series),
        "agents": _pad_series([max(1, len(scr_points))] * len(scr_points) if scr_points else [0]),
        "compliance": _pad_series(compliance_series or []),
        "hitl": _pad_series(hitl_series or []),
    }
    return trend, sparklines


def _category_label(raw: str) -> str:
    cleaned = raw.replace("_", " ").replace("-", " ").strip()
    return cleaned.title() if cleaned else "Code Analysis"


def _build_dashboard_widgets(
    scr_snapshots: list[dict[str, Any]],
    priority_queue: list[dict[str, Any]],
    *,
    paused_workflows: int,
    running_workflows: int,
    completed_workflows: int,
) -> dict[str, Any]:
    vendor_map: dict[str, dict[str, Any]] = {}
    category_counts: dict[str, dict[str, Any]] = {}
    compliance_gaps: set[str] = set()
    compliance_series: list[int] = []

    for scr in scr_snapshots:
        for gap in scr.get("compliance_gaps") or []:
            if isinstance(gap, str):
                compliance_gaps.add(gap)
        gap_count = len(scr.get("compliance_gaps") or [])
        compliance_series.append(max(35, 100 - min(65, gap_count * 12)))

        sbom = scr.get("sbom_summary") or {}
        components = int(sbom.get("components") or sbom.get("total_packages") or 0)
        vulnerable = int(sbom.get("vulnerable") or sbom.get("vulnerable_packages") or 0)
        if components or vulnerable:
            name = str(sbom.get("ecosystem") or "Supply chain")
            score = min(99, 40 + vulnerable * 15 + (10 if vulnerable else 0))
            prev = vendor_map.get(name)
            if prev is None or score > prev["score"]:
                vendor_map[name] = {
                    "name": name,
                    "score": score,
                    "issue": f"{vulnerable} vulnerable of {components or vulnerable} packages",
                    "severity": "high" if score >= 70 else "medium" if score >= 50 else "low",
                }

        for finding in scr.get("top_findings") or []:
            category = str(finding.get("category") or finding.get("owasp_category") or "code")
            sev = str(finding.get("severity", "medium")).lower()
            label = _category_label(category)
            bucket = category_counts.setdefault(label, {"region": label, "count": 0, "severity": sev, "source": "unishield-scr"})
            bucket["count"] += 1
            if _SEVERITY_RANK.get(sev, 4) < _SEVERITY_RANK.get(bucket["severity"], 4):
                bucket["severity"] = sev

            if category.lower() in {"dependency", "supply_chain", "sbom"} or finding.get("package_name"):
                pkg = str(finding.get("package_name") or finding.get("file_path") or "Dependency")
                cvss = int(float(finding.get("cvss_score") or finding.get("confidence") or 0) * 10)
                score = min(99, max(35, cvss or (80 if sev == "critical" else 60 if sev == "high" else 45)))
                prev = vendor_map.get(pkg)
                if prev is None or score > prev["score"]:
                    vendor_map[pkg] = {
                        "name": pkg[:48],
                        "score": score,
                        "issue": str(finding.get("category") or finding.get("cwe_name") or "Supply chain risk"),
                        "severity": sev,
                    }

    vendor_risks = sorted(vendor_map.values(), key=lambda v: v["score"], reverse=True)[:6]
    threat_origins = sorted(category_counts.values(), key=lambda x: x["count"], reverse=True)[:6]

    critical_summary = [
        {"title": item["title"], "severity": item["severity"]}
        for item in priority_queue
        if item.get("severity") in ("critical", "high")
    ][:6]

    latest = scr_snapshots[-1] if scr_snapshots else {}
    latest_risk = int(latest.get("risk_score") or 0)
    top_title = priority_queue[0]["title"] if priority_queue else "No correlated SCR signals yet"
    gap_count = len(compliance_gaps)
    compliance_pct = max(35, 100 - min(65, gap_count * 8)) if scr_snapshots else None

    ai_brief = {
        "headline": top_title,
        "tabs": {
            "exec": (
                f"Latest SCR workflow scored {latest_risk}/100 with "
                f"{sum(1 for q in priority_queue if q.get('severity') == 'critical')} critical findings."
            ),
            "soc": (
                f"{running_workflows} workflow(s) running, {paused_workflows} paused for approval. "
                f"Top signal: {top_title}."
            ),
            "compliance": (
                f"{gap_count} compliance gap(s) identified across completed code reviews. "
                f"Posture estimate {compliance_pct or 82}%."
            ),
        },
    }

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in priority_queue:
        sev = str(item.get("severity", "medium")).lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    total_sev = sum(severity_counts.values()) or 1
    severity_mix = {
        key: round((count / total_sev) * 100)
        for key, count in severity_counts.items()
    }

    hitl_series = _pad_series([paused_workflows] * max(1, len(scr_snapshots)) if scr_snapshots else [paused_workflows])

    return {
        "vendor_risks": vendor_risks,
        "threat_origins": threat_origins,
        "critical_summary": critical_summary,
        "ai_brief": ai_brief,
        "compliance_pct": compliance_pct,
        "severity_mix": severity_mix,
        "compliance_series": compliance_series,
        "hitl_series": hitl_series,
        "completed_workflows": completed_workflows,
    }


class WorkflowTriggerBody(BaseModel):
    workflow_id: str
    client_id: str
    repo_url: Optional[str] = None
    repo_ref: Optional[str] = None
    incident_id: Optional[str] = None
    source: str = "manual_frontend"


class WorkflowApproveBody(BaseModel):
    approved_by: str = Field(..., min_length=1)


def _verify_workflow_tenant(workflow: dict[str, Any] | None, client_id: str) -> dict[str, Any]:
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Cross-tenant workflow access denied")
    return workflow


@router.get("/health")
async def orchestrator_health(
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    """Check connectivity to the workflow orchestrator service."""
    try:
        data = await orchestrator_client.health()
        return {"orchestrator": data, "reachable": True}
    except OrchestratorUnavailable as exc:
        return {"orchestrator": None, "reachable": False, "error": str(exc)}


@router.get("/definitions")
async def workflow_definitions(
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    try:
        return await orchestrator_client.list_definitions()
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/metrics/{client_id}")
async def workflow_metrics(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    """Dashboard adapter — aggregate orchestrator workflow stats for Admin Center KPIs."""
    enforce_tenant(user, client_id)
    try:
        workflows = await orchestrator_client.list_workflows(client_id, limit=50)
    except OrchestratorUnavailable:
        return {"available": False, "source": "orchestrator", "has_data": False}

    running = sum(1 for w in workflows if w.get("status") == "RUNNING")
    completed = sum(1 for w in workflows if w.get("status") == "COMPLETED")
    failed = sum(1 for w in workflows if w.get("status") == "FAILED")
    paused = sum(1 for w in workflows if w.get("status") == "PAUSED")

    scr_points, priority_queue, scr_snapshots = await _build_scr_series(workflows)
    widgets = _build_dashboard_widgets(
        scr_snapshots,
        priority_queue,
        paused_workflows=paused,
        running_workflows=running,
        completed_workflows=completed,
    )
    trend, sparklines = _build_trend_and_sparklines(
        scr_points,
        compliance_series=widgets.get("compliance_series"),
        hitl_series=widgets.get("hitl_series"),
    )
    agent_rows = _build_workflow_agents(workflows)

    latest_risk = scr_points[-1]["risk_score"] if scr_points else 0
    total_findings = sum(int(p.get("total_findings") or 0) for p in scr_points)
    critical_findings = sum(int(p.get("critical_findings") or 0) for p in scr_points)
    agents_active = sum(1 for a in agent_rows if a["status"] in ("running", "listening"))
    agents_total = len(agent_rows) or len(_DEFAULT_WORKFLOW_AGENTS)
    has_data = bool(scr_points or running or paused or priority_queue)

    return {
        "available": True,
        "has_data": has_data,
        "source": "orchestrator",
        "running_workflows": running,
        "completed_workflows": completed,
        "failed_workflows": failed,
        "paused_workflows": paused,
        "kpis": {
            "risk_score": latest_risk / 100 if latest_risk > 1 else latest_risk,
            "risk_label": _risk_label_from_score(latest_risk),
            "total_findings": total_findings,
            "critical_findings": critical_findings,
            "active_alerts": len(priority_queue) or (running + paused),
            "hitl_queue": paused,
            "compliance_pct": widgets.get("compliance_pct"),
        },
        "risk_trend": trend,
        "kpi_sparklines": sparklines,
        "priority_queue": priority_queue[:12],
        "vendor_risks": widgets.get("vendor_risks") or [],
        "threat_origins": widgets.get("threat_origins") or [],
        "critical_summary": widgets.get("critical_summary") or [],
        "ai_brief": widgets.get("ai_brief"),
        "severity_mix": widgets.get("severity_mix") or {},
        "agents": agent_rows,
        "agents_active": agents_active or running,
        "agents_total": agents_total,
    }


@router.get("/{client_id}")
async def list_client_workflows(
    client_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> list[dict[str, Any]]:
    enforce_tenant(user, client_id)
    try:
        return await orchestrator_client.list_workflows(client_id, status=status, limit=limit)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/trigger")
async def trigger_workflow(
    client_id: str,
    body: WorkflowTriggerBody,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    if body.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")
    payload = body.model_dump()
    try:
        return await orchestrator_client.trigger(payload)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{client_id}/{workflow_id}")
async def get_client_workflow(
    client_id: str,
    workflow_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    try:
        workflow = await orchestrator_client.get_workflow(workflow_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _verify_workflow_tenant(workflow, client_id)


@router.get("/{client_id}/{workflow_id}/output")
async def get_client_workflow_output(
    client_id: str,
    workflow_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    try:
        workflow = await orchestrator_client.get_workflow(workflow_id)
        _verify_workflow_tenant(workflow, client_id)
        output = await orchestrator_client.get_output(workflow_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not output:
        raise HTTPException(status_code=404, detail="Workflow output not found")
    return output


@router.get("/{client_id}/{workflow_id}/actions")
async def list_client_workflow_actions(
    client_id: str,
    workflow_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> list[dict[str, Any]]:
    enforce_tenant(user, client_id)
    try:
        workflow = await orchestrator_client.get_workflow(workflow_id)
        _verify_workflow_tenant(workflow, client_id)
        return await orchestrator_client.list_actions(workflow_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/{workflow_id}/approve")
async def approve_client_workflow(
    client_id: str,
    workflow_id: str,
    body: WorkflowApproveBody,
    user: CurrentUser = Depends(require_permission("hitl:decide")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    try:
        workflow = await orchestrator_client.get_workflow(workflow_id)
        _verify_workflow_tenant(workflow, client_id)
        return await orchestrator_client.approve_workflow(workflow_id, body.approved_by)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
