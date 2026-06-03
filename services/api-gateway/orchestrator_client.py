"""HTTP client for the UniShield workflow orchestrator (unishield/ service)."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

ORCHESTRATOR_BASE = os.getenv("UNISHIELD_ORCHESTRATOR_URL", "http://localhost:8001").rstrip("/")
ORCHESTRATOR_TIMEOUT = float(os.getenv("UNISHIELD_ORCHESTRATOR_TIMEOUT", "30"))


class OrchestratorUnavailable(Exception):
    """Orchestrator service is down or unreachable."""


class OrchestratorClient:
    """Thin async proxy to orchestrator REST API."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = ORCHESTRATOR_TIMEOUT) -> None:
        self.base_url = (base_url or ORCHESTRATOR_BASE).rstrip("/")
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, params=params, json=json_body)
        except httpx.RequestError as exc:
            raise OrchestratorUnavailable(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                detail = payload.get("detail", detail)
            except Exception:
                pass
            raise OrchestratorUnavailable(f"Orchestrator error {response.status_code}: {detail}")
        if not response.content:
            return None
        return response.json()

    async def health(self) -> dict[str, Any]:
        result = await self._request("GET", "/health")
        return result or {"status": "unknown"}

    async def list_definitions(self) -> dict[str, Any]:
        return await self._request("GET", "/workflows/definitions") or {}

    async def list_workflows(
        self,
        client_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"client_id": client_id, "limit": limit}
        if status:
            params["status"] = status
        result = await self._request("GET", "/workflows/", params=params)
        return result if isinstance(result, list) else []

    async def get_workflow(self, workflow_id: str) -> Optional[dict[str, Any]]:
        return await self._request("GET", f"/workflows/{workflow_id}")

    async def get_output(self, workflow_id: str) -> Optional[dict[str, Any]]:
        return await self._request("GET", f"/workflows/{workflow_id}/output")

    async def trigger(self, body: dict[str, Any]) -> dict[str, Any]:
        result = await self._request("POST", "/workflows/trigger", json_body=body)
        return result or {}

    async def list_actions(self, workflow_id: str) -> list[dict[str, Any]]:
        result = await self._request("GET", f"/workflows/{workflow_id}/actions")
        return result if isinstance(result, list) else []

    async def approve_workflow(self, workflow_id: str, approved_by: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/workflows/{workflow_id}/approve",
            json_body={"approved_by": approved_by},
        ) or {}

    async def approve_action(self, workflow_id: str, action_id: str, approved_by: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/workflows/{workflow_id}/actions/{action_id}/approve",
            json_body={"approved_by": approved_by},
        ) or {}


orchestrator_client = OrchestratorClient()
