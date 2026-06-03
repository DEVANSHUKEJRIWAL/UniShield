"""Workflow orchestrator BFF — proxies unishield/ API through api-gateway."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.api_gateway.orchestrator_client import OrchestratorClient, OrchestratorUnavailable, orchestrator_client

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


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
        return {"available": False, "source": "orchestrator"}

    running = sum(1 for w in workflows if w.get("status") == "RUNNING")
    completed = sum(1 for w in workflows if w.get("status") == "COMPLETED")
    failed = sum(1 for w in workflows if w.get("status") == "FAILED")
    paused = sum(1 for w in workflows if w.get("status") == "PAUSED")

    latest_risk = 0
    latest_label = "Low"
    total_findings = 0
    critical_findings = 0
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
        if risk >= latest_risk:
            latest_risk = risk
            latest_label = scr.get("highest_severity") or "LOW"
        for finding in scr.get("top_findings") or []:
            sev = str(finding.get("severity", "medium")).lower()
            total_findings += 1
            if sev == "critical":
                critical_findings += 1
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

    priority_queue.sort(
        key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4)
    )

    return {
        "available": True,
        "source": "orchestrator",
        "running_workflows": running,
        "completed_workflows": completed,
        "failed_workflows": failed,
        "paused_workflows": paused,
        "kpis": {
            "risk_score": latest_risk / 100 if latest_risk > 1 else latest_risk,
            "risk_label": latest_label,
            "total_findings": total_findings,
            "critical_findings": critical_findings,
            "active_alerts": running + paused,
        },
        "priority_queue": priority_queue[:12],
        "agents_active": running,
        "agents_total": 3,
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
