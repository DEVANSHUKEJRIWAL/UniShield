"""Cloud CSPM scan API."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from packages.core.persistence import persist_finding
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.connector_registry.registry import registry

router = APIRouter(prefix="/api/v1/cloud", tags=["cloud"])


class CspmScanRequest(BaseModel):
    client_id: str
    connector: str = "guardduty"
    config: dict[str, Any] = Field(default_factory=dict)


@router.post("/cspm/scan")
async def run_cspm_scan(
    body: CspmScanRequest,
    user: CurrentUser = Depends(require_permission("write:alerts")),
) -> dict[str, Any]:
    """Run AWS GuardDuty / CSPM connector and persist cloud findings."""
    enforce_tenant(user, body.client_id)
    if body.connector not in registry.list_connectors():
        raise HTTPException(status_code=404, detail="Connector not found")
    connector = registry.get(body.connector, body.client_id, body.config)
    events = await connector.ingest()
    persisted: list[str] = []
    for event in events:
        if event.get("source_type") != "cspm" and not event.get("title"):
            continue
        title = event.get("title") or event.get("message", "Cloud CSPM finding")
        severity = str(event.get("severity", "medium")).lower()
        if severity.replace(".", "").isdigit():
            score = float(severity)
            severity = "critical" if score >= 7 else "high" if score >= 4 else "medium"
        if severity not in ("critical", "high", "medium", "low"):
            severity = "medium"
        fid = await persist_finding(
            {
                "tenant_id": body.client_id,
                "agent_id": "cloud-security-agent",
                "type": "cspm",
                "severity": severity,
                "confidence": 0.88 if not event.get("mock") else 0.72,
                "title": title[:200],
                "description": (event.get("description") or title)[:500],
                "reasoning_summary": f"CSPM ingest via {body.connector}",
                "evidence_references": [event.get("resource", {})],
            }
        )
        persisted.append(str(fid))
    return {
        "client_id": body.client_id,
        "connector": body.connector,
        "events": len(events),
        "persisted_findings": persisted,
        "sample": events[0] if events else None,
    }
