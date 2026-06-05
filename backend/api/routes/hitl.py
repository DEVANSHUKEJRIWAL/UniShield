"""HITL queue and decision API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/hitl", tags=["hitl"])


class HitlDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accept|modify|reject)$")
    decided_by: str = Field(..., min_length=1)
    workflow_id: str | None = None
    reason: str | None = None
    modification: str | None = None


def _get_hitl_service():
    from backend.api.main import get_hitl_service

    return get_hitl_service()


def _get_orchestrator():
    from backend.api.main import get_orchestrator

    return get_orchestrator()


def _get_action_gate():
    from backend.api.main import get_action_gate

    return get_action_gate()


@router.get("/queue/{client_id}")
async def hitl_queue(client_id: str) -> list[dict]:
    return await _get_hitl_service().list_queue(client_id)


@router.post("/{action_id}/decide")
async def hitl_decide(
    action_id: str,
    body: HitlDecisionRequest,
    client_id: str = Query(...),
) -> dict:
    orchestrator = _get_orchestrator()
    action_gate = _get_action_gate()

    workflow_id = body.workflow_id
    if action_id.startswith("WORKFLOW-"):
        workflow_id = action_id.removeprefix("WORKFLOW-")
    elif action_id.startswith("FINDING-") and not workflow_id:
        rest = action_id.removeprefix("FINDING-")
        parts = rest.split("-")
        if len(parts) >= 2 and parts[0] == "WF":
            workflow_id = f"{parts[0]}-{parts[1]}"

    if workflow_id and action_id.startswith(("WORKFLOW-", "FINDING-")):
        if body.decision == "accept":
            state = await orchestrator.state_store.load(workflow_id)
            if state and state.client_id != client_id:
                raise HTTPException(status_code=403, detail="Cross-tenant HITL access denied")
            if state and state.paused:
                await orchestrator.approve_workflow(workflow_id, body.decided_by)
            return {"action_id": action_id, "status": "workflow_approved", "workflow_id": workflow_id}
        if body.decision == "reject":
            return {"action_id": action_id, "status": "rejected", "workflow_id": workflow_id}
        raise HTTPException(status_code=400, detail="Use accept or reject for workflow review items")

    if body.decision == "accept":
        await action_gate.approve(action_id, body.decided_by)
        return {"action_id": action_id, "status": "approved"}
    if body.decision == "reject":
        await action_gate.reject(action_id, body.decided_by, body.reason or "Rejected by operator")
        return {"action_id": action_id, "status": "rejected"}
    await action_gate.reject(
        action_id,
        body.decided_by,
        body.modification or body.reason or "Modified by operator",
    )
    return {"action_id": action_id, "status": "modified"}
