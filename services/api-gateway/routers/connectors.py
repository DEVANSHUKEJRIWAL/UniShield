"""Connector management and ingest API (Week 7)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.connector_registry.registry import registry
from services.connector_registry.worker import ingest_connector, run_ingest_cycle

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


class ConnectorTestRequest(BaseModel):
    client_id: str
    connector: str
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorIngestRequest(BaseModel):
    client_id: str
    connectors: list[str] = Field(default_factory=lambda: ["splunk", "qradar"])


def _validate_connector_config(config: dict[str, Any]) -> None:
    """Reject obvious injection patterns in connector credentials."""
    forbidden = (";", "--", "DROP ", "UNION ", "../", "${", "{{")
    for key, value in config.items():
        text = str(value)
        if any(patt in text.upper() for patt in forbidden):
            raise HTTPException(status_code=400, detail=f"Invalid characters in connector config field: {key}")


@router.get("/registry")
async def list_connectors(
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """List registered connector adapters."""
    return {"connectors": registry.list_connectors(), "count": len(registry.list_connectors())}


@router.post("/test")
async def test_connector(
    body: ConnectorTestRequest,
    user: CurrentUser = Depends(require_permission("read:agents")),
) -> dict[str, Any]:
    """Test connector credentials without persisting."""
    enforce_tenant(user, body.client_id)
    _validate_connector_config(body.config)
    if body.connector not in registry.list_connectors():
        raise HTTPException(status_code=404, detail="Connector not found")
    try:
        connector = registry.get(body.connector, body.client_id, body.config)
        events = await connector.ingest()
        return {
            "connector": body.connector,
            "status": "ok",
            "event_count": len(events),
            "sample": events[0] if events else None,
        }
    except Exception as exc:
        return {"connector": body.connector, "status": "error", "message": str(exc)}


@router.post("/ingest")
async def trigger_ingest(
    body: ConnectorIngestRequest,
    user: CurrentUser = Depends(require_permission("write:alerts")),
) -> dict[str, Any]:
    """Manually trigger SIEM connector ingest cycle."""
    enforce_tenant(user, body.client_id)
    results: dict[str, int] = {}
    for name in body.connectors:
        if name not in registry.list_connectors():
            continue
        results[name] = await ingest_connector(name, body.client_id, {})
    return {"client_id": body.client_id, "ingested": results}
