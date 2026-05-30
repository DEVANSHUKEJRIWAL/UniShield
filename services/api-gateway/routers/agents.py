"""Agent API routes."""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.registry import AGENT_CLASSES, create_agent
from agents.orchestrator.agent import OrchestratorAgent
from packages.core.agent_messages import AgentTaskMessage
from packages.core.database import get_db
from packages.core.models import AgentRunLog, AgentState, Finding
from packages.core.redis_client import publish_stream
from packages.shared_types.constants import AgentName, RedisStream
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission
from services.risk_engine.service import risk_engine

router = APIRouter(tags=["agents"])


class AgentRunRequest(BaseModel):
    agent_name: str
    tenant_id: str
    input: dict[str, Any] = Field(default_factory=dict)


class OrchestrateRequest(BaseModel):
    tenant_id: str
    event: dict[str, Any] = Field(default_factory=dict)


@router.get("/agent/status")
async def agent_status_public() -> dict[str, Any]:
    """Public agent health (Phase 1 bridge)."""
    return {
        "agents": [{"name": n.value, "status": "idle", "healthy": True} for n in AgentName]
    }


@router.post("/agent/run")
async def agent_run_public(request: AgentRunRequest) -> StreamingResponse:
    """Trigger agent with SSE stream (Phase 1 bridge)."""
    return StreamingResponse(
        _agent_sse(request.agent_name, request.tenant_id, request.input),
        media_type="text/event-stream",
    )


@router.post("/agent/orchestrate")
async def orchestrate_public(request: OrchestrateRequest) -> StreamingResponse:
    """Run orchestrator multi-agent workflow with SSE progress."""
    return StreamingResponse(
        _orchestrate_sse(request.tenant_id, request.event),
        media_type="text/event-stream",
    )


async def _orchestrate_sse(tenant_id: str, event: dict[str, Any]) -> AsyncGenerator[str, None]:
    yield f'data: {json.dumps({"status": "started", "workflow": "orchestrator"})}\n\n'
    try:
        orchestrator = OrchestratorAgent(agent_id=f"orch-{tenant_id}", tenant_id=tenant_id)
        result = await orchestrator.orchestrate(event)
        yield f'data: {json.dumps({"status": "completed", "result": result})}\n\n'
    except Exception as exc:
        yield f'data: {json.dumps({"status": "error", "message": str(exc)})}\n\n'


async def _agent_sse(agent_name: str, tenant_id: str, input_data: dict[str, Any]) -> AsyncGenerator[str, None]:
    yield f'data: {json.dumps({"status": "started", "agent": agent_name})}\n\n'
    try:
        agent = create_agent(agent_name, tenant_id)
        result = await agent.reason(json.dumps(input_data), kg_context={"tenant_id": tenant_id})
        yield f'data: {json.dumps({"status": "completed", "result": result[:500]})}\n\n'
    except Exception as exc:
        yield f'data: {json.dumps({"status": "error", "message": str(exc)})}\n\n'


@router.post("/api/v1/agents/run")
async def run_agent(
    request: AgentRunRequest,
    user: CurrentUser = Depends(require_permission("read:agents")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger agent manually."""
    enforce_tenant(user, request.tenant_id)
    if request.agent_name not in AGENT_CLASSES:
        raise HTTPException(status_code=404, detail="Agent not found")
    task = AgentTaskMessage(
        tenant_id=request.tenant_id,
        input=request.input,
        triggered_by=user.email,
    )
    await publish_stream(
        RedisStream.agent_tasks(request.agent_name),
        task.model_dump(mode="json"),
    )
    return {"status": "queued", "agent": request.agent_name}


@router.get("/api/v1/agents/status/{client_id}")
async def agents_status(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:agents")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """All agent health for a client."""
    enforce_tenant(user, client_id)
    result = await db.execute(select(AgentState).where(AgentState.tenant_id == client_id))
    states = result.scalars().all()
    if not states:
        return {
            "client_id": client_id,
            "agents": [{"name": n.value, "status": "idle", "healthy": True} for n in AgentName],
        }
    return {
        "client_id": client_id,
        "agents": [
            {"name": s.agent_name, "status": s.status, "healthy": s.health == "healthy", "last_run": s.last_run_at}
            for s in states
        ],
    }


@router.get("/api/v1/agents/{agent_id}/runs")
async def agent_run_history(
    agent_id: str,
    client_id: str,
    limit: int = 50,
    user: CurrentUser = Depends(require_permission("read:agents")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Agent execution history (Week 3/6)."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(AgentRunLog)
        .where(AgentRunLog.agent_name == agent_id, AgentRunLog.tenant_id == client_id)
        .order_by(AgentRunLog.started_at.desc())
        .limit(min(limit, 100))
    )
    return [
        {
            "id": str(r.id),
            "task_id": r.task_id,
            "status": r.status,
            "input": r.input_data,
            "output": r.output,
            "tool_calls": r.tool_calls,
            "error": r.error,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in result.scalars().all()
    ]


@router.get("/api/v1/agents/{agent_id}/findings")
async def agent_findings(
    agent_id: str,
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:agents")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Agent output history."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(Finding).where(Finding.tenant_id == client_id, Finding.agent_id == agent_id).limit(50)
    )
    findings = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "title": f.title,
            "severity": f.severity,
            "confidence": f.confidence,
            "created_at": f.created_at.isoformat(),
        }
        for f in findings
    ]


@router.get("/api/v1/agents/stream/sse/{client_id}")
async def agent_stream_sse(client_id: str, user: CurrentUser = Depends(require_permission("read:agents"))) -> StreamingResponse:
    """SSE stream for agent outputs."""
    enforce_tenant(user, client_id)

    async def stream() -> AsyncGenerator[str, None]:
        yield f'data: {json.dumps({"client_id": client_id, "status": "connected"})}\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream")
