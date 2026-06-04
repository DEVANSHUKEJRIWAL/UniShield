"""Workflow finalizer — persist snapshot, verify, clear Redis, emit event."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from unishield.orchestrator.workflow_state import WorkflowStateStore

SCR_REQUIRED_WORKFLOWS = frozenset({"code-review-only", "compliance-readiness", "full-security-audit"})

logger = logging.getLogger(__name__)


class DataIntegrityError(Exception):
    """Raised when DB checksum verification fails."""


class WorkflowFinalizer:
    """Handles workflow completion: snapshot → DB → verify → clear → emit."""

    def __init__(
        self,
        shared_memory: SharedMemoryClient,
        postgres: PostgresClient,
        kafka: KafkaClient,
        state_store: WorkflowStateStore,
    ) -> None:
        self._shared_memory = shared_memory
        self._postgres = postgres
        self._kafka = kafka
        self._state_store = state_store

    async def finalize(
        self,
        workflow_id: str,
        client_id: str,
        *,
        workflow_name: str | None = None,
    ) -> None:
        state = await self._state_store.load(workflow_id)
        resolved_workflow_name = workflow_name or (state.workflow_name if state else None)
        snapshot = await self._shared_memory.get_full_snapshot(workflow_id)

        needs_scr = resolved_workflow_name in SCR_REQUIRED_WORKFLOWS or (
            resolved_workflow_name is None
            and "scr" not in snapshot
            and "cma" in snapshot
            and "reporting" in snapshot
            and not {"asm", "cloudsec", "web", "insider", "af"}.intersection(snapshot)
        )

        if needs_scr and "scr" not in snapshot:
            logger.error(
                "Workflow %s (%s) finalized without SCR output — recording placeholder",
                workflow_id,
                resolved_workflow_name or "unknown",
            )
            error_message = "SCR output missing at finalize"
            if state:
                error_message = state.context.get("error") or error_message
            snapshot["scr"] = {
                "agent_id": "scr",
                "scan_status": "FAILED",
                "error_message": error_message,
                "risk_score": 0,
                "highest_severity": "LOW",
                "requires_human_approval": False,
                "auto_remediation_safe": True,
                "forward_to": [],
                "critical_count": 0,
                "secret_findings_count": 0,
                "correlated_to_incident": False,
                "files_discovered": 0,
                "top_findings": [],
            }

        snapshot_json = json.loads(json.dumps(snapshot, default=str))
        if resolved_workflow_name:
            snapshot_json["_workflow_name"] = resolved_workflow_name

        checksum = hashlib.sha256(
            json.dumps(snapshot_json, sort_keys=True).encode()
        ).hexdigest()

        completed_at = datetime.now(UTC)
        await self._postgres.execute(
            """
            INSERT INTO workflow_outputs
                (workflow_id, client_id, snapshot, checksum, completed_at)
            VALUES ($1, $2, $3::jsonb, $4, $5)
            ON CONFLICT (workflow_id) DO UPDATE SET
                snapshot = EXCLUDED.snapshot,
                checksum = EXCLUDED.checksum,
                completed_at = EXCLUDED.completed_at
            """,
            workflow_id,
            client_id,
            json.dumps(snapshot_json),
            checksum,
            completed_at.replace(tzinfo=None),
        )

        row = await self._postgres.fetchrow(
            "SELECT checksum FROM workflow_outputs WHERE workflow_id = $1",
            workflow_id,
        )
        if not row or row["checksum"] != checksum:
            raise DataIntegrityError(f"Checksum mismatch for workflow {workflow_id}")

        await self._shared_memory.clear_workflow(workflow_id)

        try:
            await self._kafka.publish(
                "workflow.completed",
                {
                    "workflow_id": workflow_id,
                    "client_id": client_id,
                    "status": "SUCCESS",
                    "fetch_from": "database",
                },
                key=workflow_id,
            )
        except Exception:
            logger.exception(
                "Kafka publish failed for workflow.completed (%s) — output persisted in Postgres",
                workflow_id,
            )

        await self._state_store.complete(workflow_id)
        logger.info("Workflow %s finalized successfully", workflow_id)
