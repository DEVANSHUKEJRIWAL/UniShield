"""Live SCR stage progress for workflow UI polling."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

import redis.asyncio as aioredis

StageStatus = Literal["pending", "running", "done", "failed"]

SCR_STAGES: list[tuple[str, str]] = [
    ("acquisition", "Source acquisition"),
    ("detection", "Language & framework detection"),
    ("sast", "SAST analysis"),
    ("secrets", "Secrets scan"),
    ("sbom", "SBOM & dependencies"),
    ("dataflow", "Dataflow & taint"),
    ("ai_analysis", "AI semantic enrichment"),
    ("threat_intel", "Threat intel correlation"),
    ("ranking", "Dedup & risk ranking"),
    ("output", "Output assembly"),
]

DEFAULT_TTL = 86400


class ScrProgressTracker:
    """Tracks per-stage SCR progress in Redis for the workflow detail UI."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _key(self, workflow_id: str) -> str:
        return f"scr_progress:{workflow_id}"

    async def start(self, workflow_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        stages = [
            {"id": stage_id, "label": label, "status": "pending", "detail": "", "updated_at": now}
            for stage_id, label in SCR_STAGES
        ]
        payload = {
            "workflow_id": workflow_id,
            "started_at": now,
            "current_stage": SCR_STAGES[0][0],
            "stages": stages,
        }
        await self._redis.set(self._key(workflow_id), json.dumps(payload), ex=DEFAULT_TTL)
        await self.set_stage(workflow_id, SCR_STAGES[0][0], "running")

    async def set_stage(
        self,
        workflow_id: str,
        stage_id: str,
        status: StageStatus,
        *,
        detail: str = "",
    ) -> None:
        raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            await self.start(workflow_id)
            raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            return

        data = json.loads(raw)
        now = datetime.now(UTC).isoformat()
        stage_ids = [s[0] for s in SCR_STAGES]
        current_idx = stage_ids.index(stage_id) if stage_id in stage_ids else 0

        for stage in data.get("stages", []):
            sid = stage.get("id")
            if sid == stage_id:
                stage["status"] = status
                stage["detail"] = detail
                stage["updated_at"] = now
            elif sid in stage_ids:
                idx = stage_ids.index(sid)
                if idx < current_idx and stage.get("status") not in ("done", "failed"):
                    stage["status"] = "done"
                    stage["updated_at"] = now

        if status == "done" and current_idx + 1 < len(stage_ids):
            data["current_stage"] = stage_ids[current_idx + 1]
            for stage in data["stages"]:
                if stage["id"] == stage_ids[current_idx + 1] and stage["status"] == "pending":
                    stage["status"] = "running"
                    stage["updated_at"] = now
        else:
            data["current_stage"] = stage_id

        if status == "failed":
            data["error"] = detail

        await self._redis.set(self._key(workflow_id), json.dumps(data), ex=DEFAULT_TTL)

    async def complete(self, workflow_id: str) -> None:
        raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            return
        data = json.loads(raw)
        now = datetime.now(UTC).isoformat()
        for stage in data.get("stages", []):
            stage["status"] = "done"
            stage["updated_at"] = now
        data["current_stage"] = SCR_STAGES[-1][0]
        data["completed_at"] = now
        await self._redis.set(self._key(workflow_id), json.dumps(data), ex=DEFAULT_TTL)

    async def fail(self, workflow_id: str, message: str) -> None:
        raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            await self.start(workflow_id)
            raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            return
        data = json.loads(raw)
        current = data.get("current_stage", SCR_STAGES[0][0])
        await self.set_stage(workflow_id, current, "failed", detail=message)

    async def get(self, workflow_id: str) -> dict | None:
        raw = await self._redis.get(self._key(workflow_id))
        if raw is None:
            return None
        return json.loads(raw)
