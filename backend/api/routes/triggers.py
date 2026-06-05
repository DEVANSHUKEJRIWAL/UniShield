"""External workflow triggers — CI/CD webhooks and scheduled scans."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.orchestrator.trigger_handler import TriggerHandler
from backend.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


class CicdWebhookBody(BaseModel):
    workflow_id: str = Field(default="incremental-pr-scan")
    client_id: str
    repo_url: str
    repo_ref: str = "main"
    source: str = "cicd"
    diff_base: Optional[str] = None
    diff_head: Optional[str] = None
    connection_id: Optional[str] = None
    repo_auth_token: Optional[str] = None
    incident_id: Optional[str] = None


class ScheduledScanBody(BaseModel):
    workflow_id: str = Field(default="code-review-only")
    client_id: str
    connection_id: str
    ref_override: Optional[str] = None
    scan_mode: str = "full_repo"


def _get_trigger_handler() -> TriggerHandler:
    from backend.api.main import get_orchestrator

    return TriggerHandler(get_orchestrator())


@router.post("/cicd/webhook")
async def cicd_webhook(
    body: CicdWebhookBody,
    x_unishield_token: Optional[str] = Header(None, alias="X-UniShield-Token"),
) -> dict[str, Any]:
    """CI/CD or PR webhook — starts incremental or full repo scan."""
    if body.workflow_id not in WORKFLOW_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {body.workflow_id}")

    context: dict[str, Any] = {
        "scan_mode": "incremental" if body.diff_base else "full_repo",
        "diff_base": body.diff_base,
        "diff_head": body.diff_head,
        "connection_id": body.connection_id,
        "webhook_token_present": bool(x_unishield_token),
    }
    if body.repo_auth_token:
        context["repo_auth_token"] = body.repo_auth_token

    handler = _get_trigger_handler()
    workflow_id = await handler.handle(
        workflow_name=body.workflow_id,
        client_id=body.client_id,
        source=body.source,
        incident_id=body.incident_id,
        repo_url=body.repo_url,
        repo_ref=body.repo_ref,
        context=context,
    )
    return {"workflow_id": workflow_id, "status": "started", "source": body.source}


@router.post("/scheduled/scan")
async def scheduled_scan(body: ScheduledScanBody) -> dict[str, Any]:
    """Cron-friendly endpoint to trigger a connected-repo scan."""
    from backend.api.main import get_repo_registry

    if body.workflow_id not in WORKFLOW_DEFINITIONS:
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {body.workflow_id}")

    registry = get_repo_registry()
    target = await registry.resolve_scan_target(
        body.connection_id,
        ref_override=body.ref_override,
        scan_mode=body.scan_mode,
    )
    handler = _get_trigger_handler()
    workflow_id = await handler.handle(
        workflow_name=body.workflow_id,
        client_id=body.client_id,
        source="scheduled",
        repo_url=target.repo_url,
        repo_ref=target.repo_ref,
        context={
            "connection_id": body.connection_id,
            "repo_auth_token": target.repo_auth_token,
            "include_patterns": target.include_patterns,
            "exclude_patterns": target.exclude_patterns,
            "crown_jewels": target.crown_jewel_paths,
            "scan_mode": target.scan_mode,
        },
    )
    await registry.mark_scanned(body.connection_id, workflow_id)
    return {"workflow_id": workflow_id, "status": "started", "source": "scheduled"}
