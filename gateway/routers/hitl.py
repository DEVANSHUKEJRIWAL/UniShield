"""Human-in-the-loop BFF — proxies orchestrator HITL API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from gateway.orchestrator_client import OrchestratorClient, OrchestratorUnavailable, orchestrator_client

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


class HitlDecisionBody(BaseModel):
    decision: str = Field(..., pattern="^(accept|modify|reject)$")
    workflow_id: str | None = None
    reason: str | None = None
    modification: str | None = None


@router.get("/queue/{client_id}")
async def hitl_queue(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> list[dict]:
    enforce_tenant(user, client_id)
    try:
        return await orchestrator_client.hitl_queue(client_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{action_id}/decide")
async def hitl_decide(
    action_id: str,
    body: HitlDecisionBody,
    client_id: str = Query(...),
    user: CurrentUser = Depends(require_permission("hitl:decide")),
) -> dict:
    enforce_tenant(user, client_id)
    try:
        return await orchestrator_client.hitl_decide(
            action_id,
            client_id,
            {
                "decision": body.decision,
                "decided_by": user.email,
                "workflow_id": body.workflow_id,
                "reason": body.reason,
                "modification": body.modification,
            },
        )
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
