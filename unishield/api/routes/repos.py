"""Repository connection management API."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from unishield.connectors.repo_registry import RepoNotConnectedError, RepoRegistry
from unishield.orchestrator.trigger_handler import TriggerHandler
from unishield.schemas.repo_schemas import (
    MultiRepoScanRequest,
    RepoBulkScanStatus,
    RepoConnection,
    RepoConnectionCreate,
)

router = APIRouter(prefix="/repos", tags=["repos"])

_bulk_scans: dict[str, RepoBulkScanStatus] = {}


def _get_registry() -> RepoRegistry:
    from unishield.api.main import get_repo_registry

    return get_repo_registry()


def _get_trigger_handler() -> TriggerHandler:
    from unishield.api.main import get_orchestrator

    return TriggerHandler(get_orchestrator())


class ConnectRepoBody(BaseModel):
    connection: RepoConnectionCreate
    token: str = Field(..., min_length=1)


class RotateTokenBody(BaseModel):
    token: str = Field(..., min_length=1)


class ScanRepoBody(BaseModel):
    workflow_id: str
    ref_override: Optional[str] = None
    scan_mode: str = "full_repo"
    incident_id: Optional[str] = None


@router.post("/connect", response_model=RepoConnection)
async def connect_repo(body: ConnectRepoBody) -> RepoConnection:
    registry = _get_registry()
    return await registry.register(body.connection, body.token)


@router.get("/{client_id}", response_model=list[RepoConnection])
async def list_repos(client_id: str) -> list[RepoConnection]:
    return await _get_registry().list_connections(client_id)


@router.get("/connection/{connection_id}", response_model=RepoConnection)
async def get_repo(connection_id: str) -> RepoConnection:
    try:
        return await _get_registry().get_connection(connection_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/connection/{connection_id}", response_model=RepoConnection)
async def update_repo(connection_id: str, body: RepoConnection) -> RepoConnection:
    if body.connection_id != connection_id:
        raise HTTPException(status_code=400, detail="connection_id mismatch")
    return await _get_registry().update_connection(body)


@router.delete("/connection/{connection_id}")
async def delete_repo(connection_id: str) -> dict[str, bool]:
    await _get_registry().delete_connection(connection_id)
    return {"deleted": True}


@router.post("/connection/{connection_id}/verify", response_model=RepoConnection)
async def verify_repo(connection_id: str) -> RepoConnection:
    return await _get_registry().verify_connection(connection_id)


@router.post("/connection/{connection_id}/rotate-token", response_model=RepoConnection)
async def rotate_repo_token(connection_id: str, body: RotateTokenBody) -> RepoConnection:
    return await _get_registry().rotate_token(connection_id, body.token)


@router.post("/connection/{connection_id}/scan")
async def scan_repo(connection_id: str, body: ScanRepoBody) -> dict[str, Any]:
    registry = _get_registry()
    try:
        target = await registry.resolve_scan_target(
            connection_id,
            ref_override=body.ref_override,
            scan_mode=body.scan_mode,
        )
    except RepoNotConnectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    conn = await registry.get_connection(connection_id)
    handler = _get_trigger_handler()
    workflow_id = await handler.handle(
        workflow_name=body.workflow_id,
        client_id=conn.client_id,
        source="manual_frontend",
        incident_id=body.incident_id,
        repo_url=target.repo_url,
        repo_ref=target.repo_ref,
        context={
            "connection_id": connection_id,
            "scan_target": target.model_dump(exclude={"repo_auth_token"}),
            "repo_auth_token": target.repo_auth_token,
            "exclude_patterns": target.exclude_patterns,
            "crown_jewels": target.crown_jewel_paths,
            "scan_mode": target.scan_mode,
        },
    )
    await registry.mark_scanned(connection_id, workflow_id)
    return {"workflow_id": workflow_id, "status": "started", "connection_id": connection_id}


@router.post("/scan-multiple", response_model=RepoBulkScanStatus)
async def scan_multiple(body: MultiRepoScanRequest) -> RepoBulkScanStatus:
    registry = _get_registry()
    targets = await registry.resolve_multi_repo(body)
    if not targets:
        raise HTTPException(status_code=400, detail="No connected repos to scan")

    bulk_scan_id = f"bulk-{uuid.uuid4().hex[:8]}"
    workflow_ids: dict[str, str] = {}
    handler = _get_trigger_handler()
    failed = 0
    for target in targets:
        try:
            conn = await registry.get_connection(target.connection_id)
            workflow_id = await handler.handle(
                workflow_name=body.workflow_id,
                client_id=body.client_id,
                source="manual_frontend",
                incident_id=body.incident_id,
                repo_url=target.repo_url,
                repo_ref=target.repo_ref,
                context={
                    "connection_id": target.connection_id,
                    "scan_target": target.model_dump(exclude={"repo_auth_token"}),
                    "repo_auth_token": target.repo_auth_token,
                    "exclude_patterns": target.exclude_patterns,
                    "crown_jewels": target.crown_jewel_paths,
                    "scan_mode": target.scan_mode,
                    "bulk_scan_id": bulk_scan_id,
                },
            )
            workflow_ids[target.connection_id] = workflow_id
            await registry.mark_scanned(target.connection_id, workflow_id)
        except Exception:
            failed += 1

    status = RepoBulkScanStatus(
        bulk_scan_id=bulk_scan_id,
        client_id=body.client_id,
        total_repos=len(targets),
        completed=0,
        failed=failed,
        in_progress=len(workflow_ids),
        workflow_ids=workflow_ids,
        started_at=datetime.now(UTC),
    )
    _bulk_scans[bulk_scan_id] = status
    return status


@router.get("/bulk-scan/{bulk_scan_id}", response_model=RepoBulkScanStatus)
async def get_bulk_scan(bulk_scan_id: str) -> RepoBulkScanStatus:
    status = _bulk_scans.get(bulk_scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Bulk scan not found")
    return status


@router.get("/connection/{connection_id}/branches")
async def list_branches(connection_id: str) -> dict[str, list[str]]:
    registry = _get_registry()
    conn = await registry.get_connection(connection_id)
    token = await registry.get_token(connection_id)
    connector = registry._connectors[str(conn.provider)]
    branches = await connector.list_branches(conn, token)
    return {"branches": branches}
