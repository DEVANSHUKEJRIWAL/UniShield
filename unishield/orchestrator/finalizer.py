"""Workflow finalizer — persist snapshot, verify, clear Redis, emit event."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from unishield.infrastructure.kafka_client import KafkaClient
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.orchestrator.workflow_state import WorkflowStateStore

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

    async def finalize(self, workflow_id: str, client_id: str) -> None:
        snapshot = await self._shared_memory.get_full_snapshot(workflow_id)
        snapshot_json = json.loads(json.dumps(snapshot, default=str))

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
            snapshot_json,
            checksum,
            completed_at,
        )

        row = await self._postgres.fetchrow(
            "SELECT checksum FROM workflow_outputs WHERE workflow_id = $1",
            workflow_id,
        )
        if not row or row["checksum"] != checksum:
            raise DataIntegrityError(f"Checksum mismatch for workflow {workflow_id}")

        await self._shared_memory.clear_workflow(workflow_id)

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

        await self._state_store.complete(workflow_id)
        logger.info("Workflow %s finalized successfully", workflow_id)
