"""Deployment status and infrastructure health (Week 9)."""

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends

from packages.core.config import settings
from services.api_gateway.dependencies import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/deployment", tags=["deployment"])


async def _probe_http(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            return {"status": "healthy" if resp.status_code < 500 else "degraded", "code": resp.status_code}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)[:120]}


@router.get("/status")
async def deployment_status(
    user: CurrentUser = Depends(require_permission("read:dashboard")),
) -> dict[str, Any]:
    """Platform component health for deployment-status page."""
    components = {
        "api_gateway": {"status": "healthy", "version": "1.0.0"},
        "postgres": {"status": "configured", "uri": settings.database_uri.split("@")[-1][:40]},
        "redis": {"status": "configured", "url": settings.redis_url},
        "neo4j": {"uri": settings.neo4j_uri, **await _probe_http("http://localhost:7474")},
        "timescaledb": {"status": "configured", "uri": settings.timescale_uri.split("@")[-1][:40]},
        "qdrant": await _probe_http(f"{settings.qdrant_url}/healthz"),
        "elasticsearch": await _probe_http(f"{settings.elasticsearch_url}/_cluster/health"),
        "vault": await _probe_http(f"{settings.vault_addr}/v1/sys/health"),
        "prometheus": await _probe_http("http://localhost:9090/-/healthy"),
        "grafana": await _probe_http("http://localhost:3001/api/health"),
    }
    return {
        "environment": os.getenv("UNISHIELD_ENV", "dev"),
        "kubernetes": os.getenv("KUBERNETES_SERVICE_HOST") is not None,
        "components": components,
        "profiles": ["infra", "app", "agents"],
        "agent_workers": os.getenv("AGENT_WORKER_MODE", "compose"),
    }
