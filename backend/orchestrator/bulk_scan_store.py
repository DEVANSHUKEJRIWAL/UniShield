"""Persisted bulk multi-repo scan status."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.schemas.repo_schemas import RepoBulkScanStatus


class BulkScanStore:
    """Redis/Postgres-backed bulk scan progress."""

    def __init__(self, redis, postgres) -> None:
        self._redis = redis
        self._postgres = postgres

    def _key(self, bulk_scan_id: str) -> str:
        return f"bulk_scan:{bulk_scan_id}"

    async def save(self, status: RepoBulkScanStatus) -> None:
        payload = status.model_dump(mode="json")
        payload["started_at"] = status.started_at.isoformat()
        await self._redis.set(self._key(status.bulk_scan_id), json.dumps(payload), ex=86400 * 7)
        await self._postgres.execute(
            """
            INSERT INTO bulk_scans (bulk_scan_id, client_id, payload, updated_at)
            VALUES ($1, $2, $3::jsonb, $4)
            ON CONFLICT (bulk_scan_id) DO UPDATE SET
                payload = EXCLUDED.payload,
                updated_at = EXCLUDED.updated_at
            """,
            status.bulk_scan_id,
            status.client_id,
            json.dumps(payload),
            datetime.now(UTC).replace(tzinfo=None),
        )

    async def load(self, bulk_scan_id: str) -> RepoBulkScanStatus | None:
        raw = await self._redis.get(self._key(bulk_scan_id))
        if raw:
            data = json.loads(raw)
            if isinstance(data.get("started_at"), str):
                data["started_at"] = datetime.fromisoformat(data["started_at"])
            return RepoBulkScanStatus(**data)
        row = await self._postgres.fetchrow(
            "SELECT payload FROM bulk_scans WHERE bulk_scan_id = $1",
            bulk_scan_id,
        )
        if not row:
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload.get("started_at"), str):
            payload["started_at"] = datetime.fromisoformat(payload["started_at"])
        return RepoBulkScanStatus(**payload)

    async def refresh_from_workflows(self, bulk_scan_id: str, state_store) -> RepoBulkScanStatus | None:
        status = await self.load(bulk_scan_id)
        if not status:
            return None
        completed = 0
        failed = 0
        in_progress = 0
        for conn_id, wf_id in status.workflow_ids.items():
            state = await state_store.load(wf_id)
            if not state:
                in_progress += 1
                continue
            if state.status == "COMPLETED":
                completed += 1
            elif state.status == "FAILED":
                failed += 1
            else:
                in_progress += 1
        updated = status.model_copy(
            update={
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
            }
        )
        await self.save(updated)
        return updated

    async def on_workflow_terminal(self, workflow_id: str, state_store) -> None:
        """Update any bulk scan that references this workflow."""
        rows = await self._postgres.fetch(
            """
            SELECT bulk_scan_id, payload FROM bulk_scans
            WHERE payload->'workflow_ids' ? $1
               OR payload::text LIKE $2
            LIMIT 20
            """,
            workflow_id,
            f"%{workflow_id}%",
        )
        for row in rows:
            bulk_id = row["bulk_scan_id"]
            await self.refresh_from_workflows(bulk_id, state_store)
