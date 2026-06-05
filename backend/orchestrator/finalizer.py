"""Workflow finalizer — persist snapshot, verify, clear Redis, emit event."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from backend.infrastructure.kafka_client import KafkaClient
from backend.infrastructure.postgres_client import PostgresClient, to_pg_timestamp
from backend.memory.shared_memory import SharedMemoryClient
from backend.orchestrator.workflow_definitions import WORKFLOW_DEFINITIONS
from backend.orchestrator.workflow_state import WorkflowStateStore

SCR_REQUIRED_WORKFLOWS = frozenset(
    {"code-review-only", "compliance-readiness", "incremental-pr-scan"}
)

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
        metrics_store=None,
    ) -> None:
        self._shared_memory = shared_memory
        self._postgres = postgres
        self._kafka = kafka
        self._state_store = state_store
        self._metrics_store = metrics_store

    async def _prepare_snapshot(
        self,
        workflow_id: str,
        *,
        workflow_name: str | None = None,
    ) -> tuple[dict, str, datetime]:
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
            error_message = "SCR output missing at finalize"
            if state:
                error_message = state.context.get("error") or error_message
            logger.error(
                "Workflow %s (%s) finalized without SCR output",
                workflow_id,
                resolved_workflow_name or "unknown",
            )
            raise DataIntegrityError(error_message)

        snapshot_json = json.loads(json.dumps(snapshot, default=str))
        if resolved_workflow_name:
            snapshot_json["_workflow_name"] = resolved_workflow_name

        checksum = hashlib.sha256(
            json.dumps(snapshot_json, sort_keys=True).encode()
        ).hexdigest()
        completed_at = datetime.now(UTC)
        return snapshot_json, checksum, completed_at

    async def _write_snapshot(
        self,
        workflow_id: str,
        client_id: str,
        snapshot_json: dict,
        checksum: str,
        completed_at: datetime,
    ) -> None:
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
            to_pg_timestamp(completed_at),
        )

        row = await self._postgres.fetchrow(
            "SELECT checksum FROM workflow_outputs WHERE workflow_id = $1",
            workflow_id,
        )
        if not row or row["checksum"] != checksum:
            raise DataIntegrityError(f"Checksum mismatch for workflow {workflow_id}")

    async def persist_snapshot(
        self,
        workflow_id: str,
        client_id: str,
        *,
        workflow_name: str | None = None,
    ) -> None:
        """Persist agent outputs to Postgres without completing the workflow."""
        snapshot_json, checksum, completed_at = await self._prepare_snapshot(
            workflow_id,
            workflow_name=workflow_name,
        )
        await self._write_snapshot(workflow_id, client_id, snapshot_json, checksum, completed_at)
        logger.info("Workflow %s snapshot persisted (awaiting approval)", workflow_id)

    async def finalize(
        self,
        workflow_id: str,
        client_id: str,
        *,
        workflow_name: str | None = None,
    ) -> None:
        snapshot_json, checksum, completed_at = await self._prepare_snapshot(
            workflow_id,
            workflow_name=workflow_name,
        )
        await self._write_snapshot(workflow_id, client_id, snapshot_json, checksum, completed_at)

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
        if self._metrics_store:
            await self._record_metrics(client_id, snapshot_json, workflow_id)
        logger.info("Workflow %s finalized successfully", workflow_id)

    async def _record_metrics(self, client_id: str, snapshot: dict, workflow_id: str) -> None:
        scr = snapshot.get("scr") or {}
        findings = scr.get("top_findings") or []
        critical = sum(1 for f in findings if str(f.get("severity", "")).lower() == "critical")
        gaps = scr.get("compliance_gaps") or []
        try:
            await self._metrics_store.record_snapshot(
                client_id,
                risk_score=int(scr.get("risk_score") or 0),
                critical_count=critical,
                findings_count=len(findings),
                compliance_gaps=len(gaps) if isinstance(gaps, list) else 0,
                workflow_id=workflow_id,
            )
        except Exception:
            logger.exception("Failed to record metrics history for %s", workflow_id)
