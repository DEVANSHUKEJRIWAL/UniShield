"""UniShield API Gateway — full platform entry point."""

import asyncio
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from packages.core.config import settings
from packages.core.database import bootstrap_dev_data
from packages.core.secrets import bootstrap_secrets_into_settings
from packages.core.api_keys import sync_anthropic_key_from_repo_dotenv
from services.api_gateway.middleware.csp import CSPMiddleware
from services.api_gateway.middleware.metrics import PrometheusMiddleware, metrics_endpoint
from services.api_gateway.routers import (
    admin,
    agents,
    alerts,
    auth,
    bfsi,
    cloud,
    compliance,
    connectors,
    cve,
    dashboard,
    deployment,
    dev,
    findings,
    hitl,
    intelligence,
    investigation,
    kg,
    metrics,
    reporting,
    risk,
    search,
    ws,
    workflows,
)


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: init database, Vault secrets, background workers."""
    bootstrap_secrets_into_settings()
    sync_anthropic_key_from_repo_dotenv()
    await bootstrap_dev_data()
    try:
        from packages.core.metrics_db import ensure_metrics_schema

        await ensure_metrics_schema()
    except Exception:
        pass
    if os.getenv("ENABLE_CONNECTOR_INGEST", "1") == "1":
        from services.connector_registry.worker import run_connector_worker

        tenant = os.getenv("UNISHIELD_TENANT_ID", "meridian-financial")
        _background_tasks.append(asyncio.create_task(run_connector_worker(tenant, interval_seconds=120)))
    if os.getenv("ENABLE_CVE_POLLER", "1") == "1":
        from services.cve_poller.service import cve_poller

        async def _cve_loop() -> None:
            while True:
                try:
                    await cve_poller.poll_and_store(hours=24)
                except Exception:
                    pass
                await asyncio.sleep(int(os.getenv("CVE_POLL_INTERVAL", "3600")))

        _background_tasks.append(asyncio.create_task(_cve_loop()))
    yield
    for task in _background_tasks:
        task.cancel()


app = FastAPI(
    title="UniShield API",
    description="AI-native cybersecurity defense platform — full stack",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(CSPMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dev.router)
app.include_router(auth.router)
app.include_router(bfsi.router)
app.include_router(agents.router)
app.include_router(dashboard.router)
app.include_router(intelligence.router)
app.include_router(alerts.router)
app.include_router(hitl.router)
app.include_router(risk.router)
app.include_router(compliance.router)
app.include_router(investigation.router)
app.include_router(kg.router)
app.include_router(findings.router)
app.include_router(search.router)
app.include_router(reporting.router)
app.include_router(cve.router)
app.include_router(admin.router)
app.include_router(ws.router)
app.include_router(connectors.router)
app.include_router(cloud.router)
app.include_router(metrics.router)
app.include_router(deployment.router)
app.include_router(workflows.router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Platform health check."""
    return HealthResponse(status="healthy")


@app.get("/metrics", tags=["metrics"], include_in_schema=False)
def prometheus_metrics():
    """Prometheus scrape endpoint."""
    return metrics_endpoint()
