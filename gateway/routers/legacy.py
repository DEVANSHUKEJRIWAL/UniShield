"""Legacy frontend API routes — derived from orchestrator workflow data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from gateway.orchestrator_client import OrchestratorClient, OrchestratorUnavailable, orchestrator_client

router = APIRouter(prefix="/api/v1", tags=["legacy"])


async def _workflows_for_client(client_id: str) -> list[dict[str, Any]]:
    try:
        return await orchestrator_client.list_workflows(client_id=client_id, limit=100)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/dashboard/{client_id}")
async def legacy_dashboard(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = "7d",
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    hours = {"24h": 24, "7d": 168, "30d": 720}[range]
    try:
        return await orchestrator_client.get_metrics_history(client_id, hours=hours)
    except OrchestratorUnavailable:
        workflows = await _workflows_for_client(client_id)
        return {
            "client_id": client_id,
            "range": range,
            "workflows_total": len(workflows),
            "workflows_running": sum(1 for w in workflows if w.get("status") == "RUNNING"),
            "workflows_paused": sum(1 for w in workflows if w.get("status") == "PAUSED"),
        }


@router.get("/dashboard/executive/{client_id}")
async def legacy_executive_dashboard(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:executive")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    data = await legacy_dashboard(client_id, "30d", user)
    return {"client_id": client_id, "executive_summary": data}


@router.get("/alerts/{client_id}")
async def legacy_alerts(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:alerts")),
) -> list[dict[str, Any]]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    alerts: list[dict[str, Any]] = []
    for wf in workflows:
        if wf.get("status") not in ("PAUSED", "FAILED", "RUNNING"):
            continue
        alerts.append(
            {
                "alert_id": f"WF-{wf.get('workflow_id')}",
                "client_id": client_id,
                "severity": "high" if wf.get("status") == "FAILED" else "medium",
                "title": f"Workflow {wf.get('workflow_name')} — {wf.get('status')}",
                "status": wf.get("status", "").lower(),
                "source": "orchestrator",
                "workflow_id": wf.get("workflow_id"),
                "created_at": wf.get("started_at"),
            }
        )
    return alerts


@router.get("/findings/{client_id}")
async def legacy_findings(
    client_id: str,
    page: int = Query(1, ge=1),
    user: CurrentUser = Depends(require_permission("read:findings")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    items: list[dict[str, Any]] = []
    for wf in workflows:
        if wf.get("status") != "COMPLETED":
            continue
        wf_id = wf.get("workflow_id")
        try:
            output = await orchestrator_client.get_output(wf_id)
        except OrchestratorUnavailable:
            continue
        if not output:
            continue
        scr = (output.get("snapshot") or {}).get("scr") or {}
        for finding in scr.get("top_findings") or []:
            items.append({**finding, "workflow_id": wf_id})
    page_size = 20
    start = (page - 1) * page_size
    return {"findings": items[start : start + page_size], "total": len(items), "page": page}


@router.get("/investigation/cases/{client_id}")
async def legacy_investigation_cases(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:investigation")),
) -> list[dict[str, Any]]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    return [
        {
            "case_id": wf.get("workflow_id"),
            "client_id": client_id,
            "title": wf.get("workflow_name"),
            "status": wf.get("status"),
            "incident_id": wf.get("incident_id"),
            "started_at": wf.get("started_at"),
        }
        for wf in workflows
        if wf.get("status") in ("RUNNING", "PAUSED", "COMPLETED")
    ]


@router.get("/investigation/{case_id}")
async def legacy_investigation_case(
    case_id: str,
    user: CurrentUser = Depends(require_permission("read:investigation")),
) -> dict[str, Any]:
    try:
        wf = await orchestrator_client.get_workflow(case_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not wf:
        raise HTTPException(status_code=404, detail="Case not found")
    progress = await orchestrator_client.get_progress(case_id)
    return {"case_id": case_id, "workflow": wf, "progress": progress}


@router.get("/metrics/trends/{client_id}")
async def legacy_metrics_trends(
    client_id: str,
    hours: int = Query(168, ge=1, le=720),
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    try:
        return await orchestrator_client.get_metrics_history(client_id, hours=hours)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/ai-brief/{client_id}")
async def legacy_ai_brief(
    client_id: str,
    range: Literal["24h", "7d", "30d"] = "7d",
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    summaries: list[str] = []
    for wf in workflows[:5]:
        if wf.get("status") != "COMPLETED":
            continue
        try:
            output = await orchestrator_client.get_output(wf["workflow_id"])
            scr = (output.get("snapshot") or {}).get("scr") or {}
            if scr.get("executive_summary"):
                summaries.append(scr["executive_summary"])
        except OrchestratorUnavailable:
            break
    return {
        "client_id": client_id,
        "range": range,
        "brief": " ".join(summaries) if summaries else "No completed SCR workflows in range.",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/compliance/{client_id}/{framework}")
async def legacy_compliance(
    client_id: str,
    framework: str,
    user: CurrentUser = Depends(require_permission("read:compliance")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    gaps: set[str] = set()
    for wf in workflows:
        if wf.get("status") != "COMPLETED":
            continue
        try:
            output = await orchestrator_client.get_output(wf["workflow_id"])
            cma = (output.get("snapshot") or {}).get("cma") or {}
            for gap in cma.get("compliance_gaps") or []:
                gaps.add(str(gap))
        except OrchestratorUnavailable:
            break
    return {"client_id": client_id, "framework": framework, "gaps": sorted(gaps)}


@router.get("/agents/status/{client_id}")
async def legacy_agent_status(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    workflows = await _workflows_for_client(client_id)
    agents: dict[str, str] = {}
    for wf in workflows:
        if wf.get("status") not in ("RUNNING", "PAUSED"):
            continue
        for agent_id, raw in (wf.get("agent_states") or {}).items():
            key = agent_id.replace("unishield-", "")
            agents[key] = str(raw).lower()
    return {"client_id": client_id, "agents": agents}
