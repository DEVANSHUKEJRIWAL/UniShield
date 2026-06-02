"""Workflow state dataclass and Redis-backed store."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Optional

import redis.asyncio as aioredis

from unishield.config.settings import settings

DEFAULT_TTL = 86400


@dataclass
class WorkflowState:
    """Runtime state for a single workflow execution."""

    workflow_id: str
    client_id: str
    incident_id: Optional[str]
    workflow_name: str
    flow_type: str  # "fixed" or "dynamic"
    triggered_by: str
    started_at: datetime
    agent_states: dict[str, str]  # agent_id → PENDING/RUNNING/DONE/FAILED
    current_step_index: int
    retry_counts: dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
    paused: bool = False
    pause_reason: Optional[str] = None
    pause_expires: Optional[datetime] = None
    approved_by: Optional[str] = None
    escalated_to_dynamic: bool = False
    completed_at: Optional[datetime] = None
    status: str = "RUNNING"  # RUNNING/PAUSED/COMPLETED/FAILED
    context: dict = field(default_factory=dict)


class WorkflowStateStore:
    """Redis-backed persistence for workflow state."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, workflow_id: str) -> str:
        return f"orchestrator:workflow:{workflow_id}"

    def _serialize(self, state: WorkflowState) -> str:
        data = asdict(state)
        for key in ("started_at", "pause_expires", "completed_at"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return json.dumps(data)

    def _deserialize(self, raw: str) -> WorkflowState:
        data = json.loads(raw)
        for key in ("started_at", "pause_expires", "completed_at"):
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return WorkflowState(**data)

    async def save(self, state: WorkflowState) -> None:
        await self._redis.set(
            self._key(state.workflow_id),
            self._serialize(state),
            ex=DEFAULT_TTL,
        )

    async def load(self, workflow_id: str) -> Optional[WorkflowState]:
        raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            return None
        return self._deserialize(raw)

    async def mark_agent_running(self, workflow_id: str, agent_id: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.agent_states[agent_id] = "RUNNING"
            await self.save(state)

    async def mark_agent_done(self, workflow_id: str, agent_id: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.agent_states[agent_id] = "DONE"
            await self.save(state)

    async def mark_agent_failed(self, workflow_id: str, agent_id: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.agent_states[agent_id] = "FAILED"
            await self.save(state)

    async def increment_retry(self, workflow_id: str, agent_id: str) -> int:
        state = await self.load(workflow_id)
        if not state:
            return 0
        count = state.retry_counts.get(agent_id, 0) + 1
        state.retry_counts[agent_id] = count
        await self.save(state)
        return count

    async def pause(self, workflow_id: str, reason: str, timeout_hours: int) -> None:
        state = await self.load(workflow_id)
        if state:
            state.paused = True
            state.pause_reason = reason
            state.status = "PAUSED"
            state.pause_expires = datetime.now(UTC) + timedelta(hours=timeout_hours)
            await self.save(state)

    async def resume(self, workflow_id: str, approved_by: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.paused = False
            state.pause_reason = None
            state.pause_expires = None
            state.approved_by = approved_by
            state.status = "RUNNING"
            await self.save(state)

    async def complete(self, workflow_id: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.status = "COMPLETED"
            state.completed_at = datetime.now(UTC)
            await self.save(state)

    async def escalate_to_dynamic(self, workflow_id: str) -> None:
        state = await self.load(workflow_id)
        if state:
            state.escalated_to_dynamic = True
            state.flow_type = "dynamic"
            await self.save(state)

    async def list_workflows(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[WorkflowState]:
        pattern = "orchestrator:workflow:*"
        states: list[WorkflowState] = []
        async for key in self._redis.scan_iter(match=pattern):
            raw = await self._redis.get(key)
            if not raw:
                continue
            state = self._deserialize(raw)
            if client_id and state.client_id != client_id:
                continue
            if status and state.status != status:
                continue
            states.append(state)
            if len(states) >= limit:
                break
        return states
