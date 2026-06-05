"""Repository connector BFF — proxies backend /repos/* through the gateway."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from gateway.orchestrator_client import OrchestratorClient, OrchestratorUnavailable, orchestrator_client

router = APIRouter(prefix="/api/v1/repos", tags=["repos"])


class RepoConnectionCreateBody(BaseModel):
    client_id: str
    provider: str
    auth_method: str = "pat"
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str = "main"
    description: Optional[str] = None
    is_crown_jewel: bool = False
    crown_jewel_paths: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    include_languages: list[str] = Field(default_factory=list)
    registered_by: str


class ConnectRepoBody(BaseModel):
    connection: RepoConnectionCreateBody
    token: str = Field(..., min_length=1)


class RotateTokenBody(BaseModel):
    token: str = Field(..., min_length=1)


class ScanRepoBody(BaseModel):
    workflow_id: str
    ref_override: Optional[str] = None
    scan_mode: str = "full_repo"
    incident_id: Optional[str] = None


class MultiRepoScanBody(BaseModel):
    client_id: str
    workflow_id: str
    connection_ids: list[str] = Field(default_factory=list)
    scan_all: bool = False
    ref_override: Optional[str] = None
    incident_id: Optional[str] = None


def _verify_repo_tenant(repo: dict[str, Any] | None, client_id: str) -> dict[str, Any]:
    if not repo:
        raise HTTPException(status_code=404, detail="Repository connection not found")
    if repo.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Cross-tenant repository access denied")
    return repo


async def _get_repo_for_tenant(connection_id: str, client_id: str) -> dict[str, Any]:
    try:
        repo = await orchestrator_client.get_repo(connection_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _verify_repo_tenant(repo, client_id)


@router.post("/connect")
async def connect_repo(
    body: ConnectRepoBody,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, body.connection.client_id)
    try:
        return await orchestrator_client.connect_repo(body.model_dump())
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{client_id}")
async def list_repos(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> list[dict[str, Any]]:
    enforce_tenant(user, client_id)
    try:
        return await orchestrator_client.list_repos(client_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{client_id}/connection/{connection_id}")
async def get_repo(
    client_id: str,
    connection_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    return await _get_repo_for_tenant(connection_id, client_id)


@router.put("/{client_id}/connection/{connection_id}")
async def update_repo(
    client_id: str,
    connection_id: str,
    body: dict[str, Any],
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    if body.get("connection_id") and body["connection_id"] != connection_id:
        raise HTTPException(status_code=400, detail="connection_id mismatch")
    await _get_repo_for_tenant(connection_id, client_id)
    body["connection_id"] = connection_id
    body["client_id"] = client_id
    try:
        return await orchestrator_client.update_repo(connection_id, body)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{client_id}/connection/{connection_id}")
async def delete_repo(
    client_id: str,
    connection_id: str,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    await _get_repo_for_tenant(connection_id, client_id)
    try:
        return await orchestrator_client.delete_repo(connection_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/connection/{connection_id}/verify")
async def verify_repo(
    client_id: str,
    connection_id: str,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    await _get_repo_for_tenant(connection_id, client_id)
    try:
        return await orchestrator_client.verify_repo(connection_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/connection/{connection_id}/rotate-token")
async def rotate_repo_token(
    client_id: str,
    connection_id: str,
    body: RotateTokenBody,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    await _get_repo_for_tenant(connection_id, client_id)
    try:
        return await orchestrator_client.rotate_repo_token(connection_id, body.token)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/connection/{connection_id}/scan")
async def scan_repo(
    client_id: str,
    connection_id: str,
    body: ScanRepoBody,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    await _get_repo_for_tenant(connection_id, client_id)
    try:
        return await orchestrator_client.scan_repo(connection_id, body.model_dump())
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{client_id}/scan-multiple")
async def scan_multiple_repos(
    client_id: str,
    body: MultiRepoScanBody,
    user: CurrentUser = Depends(require_permission("write:investigation")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    if body.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")
    try:
        return await orchestrator_client.scan_multiple_repos(body.model_dump())
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{client_id}/bulk-scan/{bulk_scan_id}")
async def get_bulk_scan(
    client_id: str,
    bulk_scan_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    enforce_tenant(user, client_id)
    try:
        status = await orchestrator_client.get_bulk_scan(bulk_scan_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not status:
        raise HTTPException(status_code=404, detail="Bulk scan not found")
    if status.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Cross-tenant bulk scan access denied")
    return status


@router.get("/{client_id}/connection/{connection_id}/branches")
async def list_repo_branches(
    client_id: str,
    connection_id: str,
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, list[str]]:
    enforce_tenant(user, client_id)
    await _get_repo_for_tenant(connection_id, client_id)
    try:
        branches = await orchestrator_client.list_repo_branches(connection_id)
    except OrchestratorUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"branches": branches}
