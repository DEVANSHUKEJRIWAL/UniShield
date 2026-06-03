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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (completed_scr_points, priority_queue) from workflow history."""
    completed_points: list[dict[str, Any]] = []
    priority_queue: list[dict[str, Any]] = []

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
    return completed_points, priority_queue


def _build_trend_and_sparklines(scr_points: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
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
        "compliance": _pad_series([]),
        "hitl": _pad_series([]),
    }
    return trend, sparklines


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

    scr_points, priority_queue = await _build_scr_series(workflows)
    trend, sparklines = _build_trend_and_sparklines(scr_points)
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
            "active_alerts": running + paused,
        },
        "risk_trend": trend,
        "kpi_sparklines": sparklines,
        "priority_queue": priority_queue[:12],
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
