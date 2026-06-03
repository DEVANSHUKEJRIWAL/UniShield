"""SCR OpenClaw lifecycle callbacks."""

from __future__ import annotations

import logging

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult

from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)


class SCRCallbackHandler(CallbackHandler):
    """Wires OpenClaw execution events into personal memory."""

    def __init__(self, personal_memory: PersonalMemoryClient, scan_id: str) -> None:
        self._memory = personal_memory
        self._scan_id = scan_id

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        await self._memory.save_scan_started(self._scan_id)
        logger.debug("SCR execution start agent=%s scan=%s", agent_id, self._scan_id)

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        await self._memory.save_scan_completed(self._scan_id, result.latency_ms)
        await self._memory.increment_token_budget(self._scan_id, max(result.latency_ms // 10, 100))

    async def on_execution_error(self, agent_id: str, error: Exception) -> None:
        logger.error("SCR execution error agent=%s: %s", agent_id, error)
        progress = await self._memory.load_scan_progress(self._scan_id) or {}
        failed = progress.get("failed_batches", [])
        batch_id = progress.get("current_batch_id", "unknown")
        if batch_id not in failed:
            failed.append(batch_id)
        await self._memory.save_scan_progress(
            self._scan_id,
            progress.get("total_batches", 0),
            progress.get("completed_batches", []),
            failed,
            batch_id,
        )
