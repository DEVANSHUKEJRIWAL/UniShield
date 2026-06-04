"""Workflow API routes."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from unishield.orchestrator.orchestrator import Orchestrator
from unishield.orchestrator.trigger_handler import TriggerHandler
from unishield.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from unishield.orchestrator.workflow_state import WorkflowStateStore
from unishield.schemas.workflow_schemas import (
    WorkflowApproveRequest,
    WorkflowStateResponse,
    WorkflowTriggerRequest,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)


def _get_orchestrator() -> Orchestrator:
    from unishield.api.main import get_orchestrator
    return get_orchestrator()


def _get_state_store() -> WorkflowStateStore:
    from unishield.api.main import get_state_store
    return get_state_store()


def _get_postgres():
    from unishield.api.main import get_postgres
    return get_postgres()


def _state_to_response(state) -> WorkflowStateResponse:
    return WorkflowStateResponse(
        workflow_id=state.workflow_id,
        client_id=state.client_id,
        incident_id=state.incident_id,
        workflow_name=state.workflow_name,
        flow_type=state.flow_type,
        triggered_by=state.triggered_by,
        started_at=state.started_at,
        agent_states=state.agent_states,
        current_step_index=state.current_step_index,
        retry_counts=state.retry_counts,
        max_retries=state.max_retries,
        paused=state.paused,
        pause_reason=state.pause_reason,
        pause_expires=state.pause_expires,
        approved_by=state.approved_by,
        escalated_to_dynamic=state.escalated_to_dynamic,
        completed_at=state.completed_at,
        status=state.status,
        error=state.context.get("error"),
    )


@router.post("/trigger")
async def trigger_workflow(body: WorkflowTriggerRequest) -> dict:
    if body.workflow_id not in WORKFLOW_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {body.workflow_id}")

    handler = TriggerHandler(_get_orchestrator())
    definition = WORKFLOW_DEFINITIONS[body.workflow_id]

    if body.connection_ids or body.scan_all_repos or body.connection_id:
        from unishield.api.main import get_repo_registry
        from unishield.schemas.repo_schemas import MultiRepoScanRequest

        registry = get_repo_registry()
        if body.connection_id and not body.connection_ids and not body.scan_all_repos:
            target = await registry.resolve_scan_target(
                body.connection_id,
                ref_override=body.ref_override or body.repo_ref,
            )
            workflow_id = await handler.handle(
                workflow_name=body.workflow_id,
                client_id=body.client_id,
                source=body.source.value,
                incident_id=body.incident_id,
                repo_url=target.repo_url,
                repo_ref=target.repo_ref,
                context={
                    "connection_id": body.connection_id,
                    "repo_auth_token": target.repo_auth_token,
                    "exclude_patterns": target.exclude_patterns,
                    "crown_jewels": target.crown_jewel_paths,
                    "scan_mode": target.scan_mode,
                    "diff_base": target.diff_base,
                    "diff_head": target.diff_head,
                },
            )
            await registry.mark_scanned(body.connection_id, workflow_id)
            return {
                "workflow_id": workflow_id,
                "status": "started",
                "estimated_minutes": definition["estimated_minutes"],
            }

        request = MultiRepoScanRequest(
            client_id=body.client_id,
            workflow_id=body.workflow_id,
            connection_ids=body.connection_ids,
            scan_all=body.scan_all_repos,
            ref_override=body.ref_override or body.repo_ref,
            incident_id=body.incident_id,
        )
        targets = await registry.resolve_multi_repo(request)
        workflow_ids: list[str] = []
        for target in targets:
            workflow_id = await handler.handle(
                workflow_name=body.workflow_id,
                client_id=body.client_id,
                source=body.source.value,
                incident_id=body.incident_id,
                repo_url=target.repo_url,
                repo_ref=target.repo_ref,
                context={
                    "connection_id": target.connection_id,
                    "repo_auth_token": target.repo_auth_token,
                    "exclude_patterns": target.exclude_patterns,
                    "crown_jewels": target.crown_jewel_paths,
                    "scan_mode": target.scan_mode,
                    "diff_base": target.diff_base,
                    "diff_head": target.diff_head,
                },
            )
            workflow_ids.append(workflow_id)
            await registry.mark_scanned(target.connection_id, workflow_id)
        return {
            "workflow_ids": workflow_ids,
            "status": "started",
            "estimated_minutes": definition["estimated_minutes"],
            "count": len(workflow_ids),
        }

    try:
        workflow_id = await handler.handle(
            workflow_name=body.workflow_id,
            client_id=body.client_id,
            source=body.source.value,
            incident_id=body.incident_id,
            repo_url=body.repo_url,
            repo_ref=body.repo_ref,
        )
    except Exception as exc:
        logger.exception("Workflow trigger setup failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "workflow_id": workflow_id,
        "status": "started",
        "estimated_minutes": definition["estimated_minutes"],
    }


@router.get("/definitions")
async def list_definitions() -> dict:
    return WORKFLOW_DEFINITIONS


@router.get("/")
async def list_workflows(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[WorkflowStateResponse]:
    store = _get_state_store()
    states = await store.list_workflows(client_id=client_id, status=status, limit=limit)
    return [_state_to_response(s) for s in states]


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> WorkflowStateResponse:
    store = _get_state_store()
    state = await store.load(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _state_to_response(state)


@router.get("/{workflow_id}/output")
async def get_workflow_output(workflow_id: str) -> dict:
    postgres = _get_postgres()
    row = await postgres.fetchrow(
        "SELECT workflow_id, client_id, snapshot, checksum, completed_at FROM workflow_outputs WHERE workflow_id = $1",
        workflow_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Workflow output not found")
    snapshot = row["snapshot"]
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)

    store = _get_state_store()
    state = await store.load(workflow_id)
    workflow_name = None
    if state:
        workflow_name = state.workflow_name
    elif isinstance(snapshot, dict):
        workflow_name = snapshot.get("_workflow_name")

    return {
        "workflow_id": row["workflow_id"],
        "client_id": row["client_id"],
        "workflow_name": workflow_name,
        "snapshot": snapshot,
        "checksum": row["checksum"],
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


@router.post("/{workflow_id}/approve")
async def approve_workflow(workflow_id: str, body: WorkflowApproveRequest) -> dict:
    orchestrator = _get_orchestrator()
    state = await _get_state_store().load(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not state.paused:
        raise HTTPException(status_code=400, detail="Workflow is not paused")
    await orchestrator.approve_workflow(workflow_id, body.approved_by)
    return {"workflow_id": workflow_id, "status": "resumed"}


class ActionRejectRequest(BaseModel):
    rejected_by: str
    reason: str


@router.get("/{workflow_id}/actions")
async def list_workflow_actions(workflow_id: str) -> list[dict]:
    from unishield.api.main import get_action_gate
    return await get_action_gate().list_for_workflow(workflow_id)


@router.post("/{workflow_id}/actions/{action_id}/approve")
async def approve_action(workflow_id: str, action_id: str, body: WorkflowApproveRequest) -> dict:
    from unishield.api.main import get_action_gate
    await get_action_gate().approve(action_id, body.approved_by)
    return {"action_id": action_id, "status": "approved"}


@router.post("/{workflow_id}/actions/{action_id}/reject")
async def reject_action(workflow_id: str, action_id: str, body: ActionRejectRequest) -> dict:
    from unishield.api.main import get_action_gate
    await get_action_gate().reject(action_id, body.rejected_by, body.reason)
    return {"action_id": action_id, "status": "rejected"}
