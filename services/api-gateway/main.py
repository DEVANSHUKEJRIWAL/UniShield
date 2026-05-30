"""UniShield API Gateway — main entry point for all UI clients."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    anthropic_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()


class AgentRunRequest(BaseModel):
    """Request to trigger an agent run."""

    agent_name: str = Field(description="Agent identifier")
    tenant_id: str = Field(description="Client tenant ID")
    input: dict[str, Any] = Field(default_factory=dict, description="Agent input payload")

    model_config = {"strict": True}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    yield


app = FastAPI(
    title="UniShield API",
    description="AI-native cybersecurity defense platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Platform health check endpoint."""
    return HealthResponse(status="healthy")


@app.get("/agent/status", tags=["agents"])
async def agent_status() -> dict[str, Any]:
    """Return health status for all registered agents."""
    from packages.shared_types.constants import AgentName

    return {
        "agents": [
            {"name": name.value, "status": "idle", "healthy": True}
            for name in AgentName
        ]
    }


@app.post("/agent/run", tags=["agents"])
async def agent_run(request: AgentRunRequest) -> StreamingResponse:
    """Trigger agent and stream response via SSE."""

    async def event_stream() -> AsyncGenerator[str, None]:
        yield f"data: {{\"status\": \"started\", \"agent\": \"{request.agent_name}\"}}\n\n"
        yield f"data: {{\"status\": \"processing\", \"tenant\": \"{request.tenant_id}\"}}\n\n"
        yield 'data: {"status": "completed", "message": "Agent stub — full implementation Week 2"}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Versioned API routes — scaffolded for Phase 2
@app.get("/api/v1/agents/status/{client_id}", tags=["agents"])
async def agents_status_v1(client_id: str) -> dict[str, Any]:
    """All agent health for a client."""
    result = await agent_status()
    result["client_id"] = client_id
    return result
