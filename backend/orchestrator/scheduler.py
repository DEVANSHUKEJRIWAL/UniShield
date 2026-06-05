"""Optional scheduled workflow triggers (cron via asyncio loop)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 300


class WorkflowScheduler:
    """Polls Redis for due scheduled jobs and fires workflow triggers."""

    def __init__(self, redis, trigger_handler_factory) -> None:
        self._redis = redis
        self._trigger_handler_factory = trigger_handler_factory
        self._task: asyncio.Task | None = None
        self._running = False
        self._poll_seconds = int(os.getenv("SCHEDULER_POLL_SECONDS", str(DEFAULT_POLL_SECONDS)))

    async def start(self) -> None:
        if self._running or os.getenv("UNISHIELD_SCHEDULER_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
        ):
            logger.info("Workflow scheduler disabled (set UNISHIELD_SCHEDULER_ENABLED=true)")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Workflow scheduler started (poll=%ds)", self._poll_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def register_job(
        self,
        job_id: str,
        *,
        run_at: datetime,
        payload: dict,
    ) -> None:
        entry = {"run_at": run_at.isoformat(), "payload": payload}
        await self._redis.set(f"scheduler:job:{job_id}", json.dumps(entry), ex=86400 * 30)

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            await asyncio.sleep(self._poll_seconds)

    async def _tick(self) -> None:
        now = datetime.now(UTC)
        keys = []
        async for key in self._redis.scan_iter("scheduler:job:*"):
            keys.append(key)
        for key in keys[:50]:
            raw = await self._redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            run_at = datetime.fromisoformat(entry["run_at"])
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=UTC)
            if now < run_at:
                continue
            payload = entry.get("payload") or {}
            handler = self._trigger_handler_factory()
            await handler.handle(
                workflow_name=payload.get("workflow_id", "code-review-only"),
                client_id=payload["client_id"],
                source="scheduled",
                repo_url=payload.get("repo_url"),
                repo_ref=payload.get("repo_ref"),
                context=payload.get("context") or {},
            )
            await self._redis.delete(key)
            next_run = run_at + timedelta(hours=int(payload.get("interval_hours", 24)))
            if payload.get("recurring"):
                await self.register_job(key.split(":")[-1], run_at=next_run, payload=payload)
