"""Handles all workflow trigger sources."""

from __future__ import annotations

import logging

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
        workflow_id = await self._orchestrator.start_workflow(trigger)
        logger.info("Triggered workflow %s (%s) from source %s", workflow_id, workflow_name, source)
        return workflow_id
