"""Shared memory client — live workspace for all agents during a workflow."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from unishield.schemas.decision_surface import AgentDecisionSurface

DEFAULT_TTL = 86400

DECISION_SURFACE_FIELDS = [
    "agent_id",
    "completed_at",
    "risk_score",
    "highest_severity",
    "requires_human_approval",
    "auto_remediation_safe",
    "forward_to",
    "critical_count",
    "secret_findings_count",
    "correlated_to_incident",
    "kill_chain_stage",
    "audit_due_days",
]

JSON_FIELDS = {
    "payload",
    "forward_to",
    "forwarded_to",
    "top_findings",
    "sbom",
    "ioc_list",
    "threat_actor_ttps",
}


class AgentOutputNotReady(Exception):
    """Raised when agent output is not yet available in shared memory."""


class SharedMemoryWriteError(Exception):
    """Raised when writing to shared memory fails."""


class SharedMemoryClient:
    """Live workspace used by all agents and read by the orchestrator."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    @staticmethod
    def _as_str(value: str | bytes | None) -> str:
        """Coerce Redis hash keys/values to str (fakeredis may return bytes)."""
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    def _key(self, workflow_id: str, agent_id: str) -> str:
        return f"shared:{workflow_id}:{agent_id}"

    def _serialize_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _deserialize_value(self, field: str | bytes, value: str | bytes | None) -> Any:
        field = self._as_str(field)
        value = self._as_str(value)
        if value in ("", "None", "null"):
            return None
        if field in JSON_FIELDS or field.endswith("_json"):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        if value in ("true", "false"):
            return value == "true"
        if field in ("risk_score", "critical_count", "secret_findings_count", "kill_chain_stage", "audit_due_days"):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        if field == "completed_at":
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return value
        return value

    async def write_agent_output(
        self,
        workflow_id: str,
        agent_id: str,
        data: dict,
        ttl_seconds: int = DEFAULT_TTL,
    ) -> None:
        try:
            key = self._key(workflow_id, agent_id)
            mapping = {k: self._serialize_value(v) for k, v in data.items()}
            await self._redis.hset(key, mapping=mapping)
            await self._redis.expire(key, ttl_seconds)
        except Exception as exc:
            raise SharedMemoryWriteError(str(exc)) from exc

    async def read_agent_output(self, workflow_id: str, agent_id: str) -> dict:
        key = self._key(workflow_id, agent_id)
        raw = await self._redis.hgetall(key)
        if not raw:
            raise AgentOutputNotReady(
                f"No output for agent {agent_id} in workflow {workflow_id}"
            )
        return {self._as_str(k): self._deserialize_value(k, v) for k, v in raw.items()}

    async def read_decision_surface(
        self,
        workflow_id: str,
        agent_id: str,
    ) -> AgentDecisionSurface:
        key = self._key(workflow_id, agent_id)
        values = await self._redis.hmget(key, DECISION_SURFACE_FIELDS)
        if not any(values):
            raise AgentOutputNotReady(
                f"Decision surface not ready for {agent_id} in workflow {workflow_id}"
            )
        data = {}
        for field, value in zip(DECISION_SURFACE_FIELDS, values):
            if value is None:
                if field in ("kill_chain_stage", "audit_due_days"):
                    data[field] = None
                elif field == "forward_to":
                    data[field] = []
                else:
                    data[field] = 0 if field.endswith("_count") or field == "risk_score" else False
            else:
                data[field] = self._deserialize_value(field, value)
        return AgentDecisionSurface(**data)

    async def read_multiple_agents(
        self,
        workflow_id: str,
        agent_ids: list[str],
    ) -> dict[str, dict]:
        results = await asyncio.gather(
            *[self.read_agent_output(workflow_id, aid) for aid in agent_ids],
            return_exceptions=True,
        )
        output: dict[str, dict] = {}
        for agent_id, result in zip(agent_ids, results):
            if isinstance(result, Exception):
                continue
            output[agent_id] = result
        return output

    async def get_full_snapshot(self, workflow_id: str) -> dict:
        pattern = f"shared:{workflow_id}:*"
        keys = [k async for k in self._redis.scan_iter(match=pattern)]
        snapshot: dict[str, dict] = {}
        for key in keys:
            key_str = self._as_str(key)
            agent_id = key_str.split(":")[-1]
            raw = await self._redis.hgetall(key)
            snapshot[agent_id] = {
                self._as_str(k): self._deserialize_value(k, v) for k, v in raw.items()
            }
        return snapshot

    async def clear_workflow(self, workflow_id: str) -> None:
        pattern = f"shared:{workflow_id}:*"
        keys = [k async for k in self._redis.scan_iter(match=pattern)]
        if keys:
            await self._redis.delete(*keys)

    async def workflow_exists(self, workflow_id: str) -> bool:
        pattern = f"shared:{workflow_id}:*"
        async for _ in self._redis.scan_iter(match=pattern, count=1):
            return True
        return False
