"""Kafka consumers for event-driven orchestration."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from backend.infrastructure.kafka_client import KafkaConsumer

if TYPE_CHECKING:
    from backend.orchestrator.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class OrchestratorEventConsumers:
    """Background Kafka consumers that drive workflow progression."""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator
        self._consumer = KafkaConsumer()
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        await self._consumer.start()
        self._running = True
        self._tasks.append(asyncio.create_task(self._consume_agent_complete()))
        logger.info("Orchestrator Kafka consumers started (agent.complete)")

    async def stop(self) -> None:
        self._running = False
        await self._consumer.stop()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _consume_agent_complete(self) -> None:
        while self._running:
            try:
                await self._consumer.consume(
                    "agent.complete",
                    "unishield-orchestrator-complete",
                    self._handle_agent_complete,
                )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("agent.complete consumer stopped — restarting in 5s")
                await asyncio.sleep(5)

    async def _handle_agent_complete(self, event: dict) -> None:
        workflow_id = event.get("workflow_id")
        if not workflow_id:
            logger.warning("agent.complete missing workflow_id: %s", event)
            return
        logger.info(
            "Kafka agent.complete workflow=%s agent=%s",
            workflow_id,
            event.get("agent_id"),
        )
        await self._orchestrator.on_agent_complete(event)
