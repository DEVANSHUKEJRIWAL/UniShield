"""Persistent repo scan memory — agents learn from prior runs on a connection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

import redis.asyncio as aioredis

DEFAULT_TTL = 60 * 60 * 24 * 90  # 90 days


class RepoMemoryClient:
    """Stores prior scan summaries per tenant + repo connection for agent context."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, client_id: str, connection_id: str) -> str:
        return f"repo_memory:{client_id}:{connection_id}"

    async def load(self, client_id: str, connection_id: str) -> Optional[dict[str, Any]]:
        raw = await self._redis.get(self._key(client_id, connection_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def save_scan_summary(
        self,
        client_id: str,
        connection_id: str,
        *,
        workflow_id: str,
        risk_score: int,
        highest_severity: str,
        total_findings: int,
        top_findings: list[dict[str, Any]],
        languages: list[str],
        frameworks: list[str],
    ) -> None:
        prior = await self.load(client_id, connection_id) or {"scan_history": []}
        history = list(prior.get("scan_history") or [])
        history.append(
            {
                "workflow_id": workflow_id,
                "completed_at": datetime.now(UTC).isoformat(),
                "risk_score": risk_score,
                "highest_severity": highest_severity,
                "total_findings": total_findings,
            }
        )
        history = history[-20:]
        payload = {
            "client_id": client_id,
            "connection_id": connection_id,
            "last_workflow_id": workflow_id,
            "last_scan_at": datetime.now(UTC).isoformat(),
            "last_risk_score": risk_score,
            "last_highest_severity": highest_severity,
            "last_total_findings": total_findings,
            "top_findings": top_findings[:20],
            "languages": languages,
            "frameworks": frameworks,
            "scan_history": history,
        }
        await self._redis.set(self._key(client_id, connection_id), json.dumps(payload), ex=DEFAULT_TTL)
