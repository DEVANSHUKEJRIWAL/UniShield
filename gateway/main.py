"""UniShield API Gateway — orchestrator + SCR workflow BFF."""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.database import bootstrap_dev_data
from core.secrets import bootstrap_secrets_into_settings
from core.api_keys import sync_anthropic_key_from_repo_dotenv
from gateway.middleware.csp import CSPMiddleware
from gateway.middleware.metrics import PrometheusMiddleware, metrics_endpoint
from gateway.routers import admin, auth, dev, hitl, repos, workflows


class HealthResponse(BaseModel):
    status: str
    version: str = "2.0.0"
    focus: str = "orchestrator-scr"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: init database and optional secrets."""
    bootstrap_secrets_into_settings()
    sync_anthropic_key_from_repo_dotenv()
    await bootstrap_dev_data()
    yield


app = FastAPI(
    title="UniShield API",
    description="Orchestrator and source code review workflow gateway",
    version="2.0.0",
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
app.include_router(admin.router)
app.include_router(workflows.router)
app.include_router(repos.router)
app.include_router(hitl.router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Platform health check."""
    return HealthResponse(status="healthy")


@app.get("/metrics", tags=["metrics"], include_in_schema=False)
def prometheus_metrics():
    """Prometheus scrape endpoint."""
    return metrics_endpoint()
