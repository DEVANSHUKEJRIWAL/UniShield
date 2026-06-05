"""4-hour human-gate escalation watcher per orchestrator skill spec."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from backend.infrastructure.kafka_client import KafkaProducer
from backend.orchestrator.workflow_state import WorkflowStateStore

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60


class HumanGateWatcher:
    """Escalates paused workflows when pause_expires is exceeded without approval."""

    def __init__(
        self,
        state_store: WorkflowStateStore,
        kafka: KafkaProducer,
        *,
        poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
    ) -> None:
        self._state_store = state_store
        self._kafka = kafka
        self._poll_interval = poll_interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Human gate watcher started (poll=%ds)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._check_expired_gates()
            except Exception:
                logger.exception("Human gate watcher tick failed")
            await asyncio.sleep(self._poll_interval)

    async def _check_expired_gates(self) -> None:
        paused = await self._state_store.list_workflows(status="PAUSED", limit=200)
        now = datetime.now(UTC)
        for state in paused:
            if not state.pause_expires or state.context.get("gate_escalated"):
                continue
            expires = state.pause_expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if now <= expires:
                continue
            await self._escalate(state)

    async def _escalate(self, state) -> None:
        state.context["gate_escalated"] = True
        state.context["gate_escalated_at"] = datetime.now(UTC).isoformat()
        state.pause_reason = (
            f"{state.pause_reason or 'Human approval required'} "
            f"(ESCALATED — no approval within timeout)"
        )
        await self._state_store.save(state)
        await self._kafka.publish(
            "workflow.human_gate_escalated",
            {
                "workflow_id": state.workflow_id,
                "client_id": state.client_id,
                "workflow_name": state.workflow_name,
                "pause_reason": state.pause_reason,
                "escalated_at": state.context["gate_escalated_at"],
                "notify": "board",
            },
            key=state.workflow_id,
        )
        logger.warning(
            "Human gate escalated for workflow %s (client=%s)",
            state.workflow_id,
            state.client_id,
        )
