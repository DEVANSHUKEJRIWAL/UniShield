"""UniShield API Gateway — full platform entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from packages.core.config import settings
from packages.core.database import init_db
from services.api_gateway.routers import (
    admin,
    agents,
    alerts,
    auth,
    compliance,
    dashboard,
    hitl,
    investigation,
    kg,
    risk,
    ws,
)


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: init database tables."""
    await init_db()
    yield


app = FastAPI(
    title="UniShield API",
    description="AI-native cybersecurity defense platform — full stack",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(dashboard.router)
app.include_router(alerts.router)
app.include_router(hitl.router)
app.include_router(risk.router)
app.include_router(compliance.router)
app.include_router(investigation.router)
app.include_router(kg.router)
app.include_router(admin.router)
app.include_router(ws.router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Platform health check."""
    return HealthResponse(status="healthy")
