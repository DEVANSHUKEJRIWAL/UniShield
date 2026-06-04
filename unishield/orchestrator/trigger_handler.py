"""Handles all workflow trigger sources."""

from __future__ import annotations

import asyncio
import logging
import os

from unishield.config.settings import settings
from unishield.orchestrator.orchestrator import Orchestrator
from unishield.schemas.workflow_schemas import TriggerSource, WorkflowTrigger

logger = logging.getLogger(__name__)

SOURCE_MAP = {
    "manual_frontend": TriggerSource.MANUAL_FRONTEND,
    "scheduled": TriggerSource.SCHEDULED,
    "cicd": TriggerSource.CICD,
    "cicd_pipeline": TriggerSource.CICD,
    "incident": TriggerSource.INCIDENT,
    "alert_escalation": TriggerSource.ALERT_ESCALATION,
    "threat_actor": TriggerSource.THREAT_ACTOR,
    "pull_request": TriggerSource.CICD,
    "manual": TriggerSource.MANUAL_FRONTEND,
    "webhook": TriggerSource.MANUAL_FRONTEND,
}


class TriggerHandler:
    """Normalizes external trigger events into workflow triggers."""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator
        self._background_tasks: set[asyncio.Task] = set()

    async def handle(
        self,
        workflow_name: str,
        client_id: str,
        source: str,
        incident_id: str | None = None,
        repo_url: str | None = None,
        repo_ref: str | None = None,
        context: dict | None = None,
    ) -> str:
        trigger_source = SOURCE_MAP.get(source, TriggerSource.MANUAL_FRONTEND)
        trigger = WorkflowTrigger(
            workflow_name=workflow_name,
            client_id=client_id,
            source=trigger_source,
            incident_id=incident_id,
            repo_url=repo_url,
            repo_ref=repo_ref,
            context=context or {},
        )
        run_inline = settings.inline_workflows or os.getenv("UNISHIELD_INLINE_WORKFLOWS", "").lower() in (
            "1",
            "true",
            "yes",
        )
        workflow_id = await self._orchestrator.start_workflow(trigger, run_inline=False)
        if run_inline:
            await self._run_in_background(workflow_id)
        else:
            task = asyncio.create_task(self._run_in_background(workflow_id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        logger.info("Triggered workflow %s (%s) from source %s", workflow_id, workflow_name, source)
        return workflow_id

    async def _run_in_background(self, workflow_id: str) -> None:
        try:
            await self._orchestrator.execute_workflow(workflow_id)
        except Exception as exc:
            logger.exception("Background execution failed for workflow %s", workflow_id)
            state = await self._orchestrator.state_store.load(workflow_id)
            if state and state.status == "RUNNING":
                await self._orchestrator.state_store.fail(workflow_id, str(exc))
                try:
                    await self._orchestrator._finalize(state)
                except Exception:
                    logger.exception("Failed to finalize workflow %s after background error", workflow_id)
