"""Context window compaction defense — re-inject instructions every batch."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from unishield.memory.personal_memory import PersonalMemoryClient


@dataclass
class BatchGuardResult:
    should_continue: bool
    stop_reason: Optional[str]
    refreshed_instructions: dict
    output_schema_reminder: str


class BatchContextGuard:
    """Re-injects critical instructions at the start of every batch."""

    def __init__(self, personal_memory: PersonalMemoryClient, scan_id: str) -> None:
        self.personal_memory = personal_memory
        self.scan_id = scan_id

    async def write_stage_config(self, stage_instructions: dict, output_schema: str) -> None:
        await self.personal_memory.save_stage_config(
            self.scan_id, stage_instructions, output_schema
        )

    async def write_stop_signal(self) -> None:
        await self.personal_memory.set_control(self.scan_id, "stop", "true")

    async def pre_batch_check(
        self,
        batch_id: str,
        batch_number: int,
        total_batches: int,
    ) -> BatchGuardResult:
        stop = await self.personal_memory.get_control(self.scan_id, "stop")
        if stop == "true":
            return BatchGuardResult(
                should_continue=False,
                stop_reason="Stop signal received from orchestrator",
                refreshed_instructions={},
                output_schema_reminder="",
            )

        pause = await self.personal_memory.get_control(self.scan_id, "pause")
        if pause == "true":
            for _ in range(10):
                await asyncio.sleep(0.01)
                pause = await self.personal_memory.get_control(self.scan_id, "pause")
                if pause != "true":
                    break

        progress = await self.personal_memory.load_scan_progress(self.scan_id)
        if progress and batch_id in progress.get("completed_batches", []):
            return BatchGuardResult(
                should_continue=False,
                stop_reason="Batch already processed",
                refreshed_instructions={},
                output_schema_reminder="",
            )

        instructions, schema = await self.personal_memory.load_stage_config(self.scan_id)
        await self.personal_memory.save_heartbeat(
            self.scan_id,
            {
                "batch_id": batch_id,
                "batch_number": batch_number,
                "total_batches": total_batches,
                "checked_at": datetime.now(UTC).isoformat(),
            },
        )
        return BatchGuardResult(
            should_continue=True,
            stop_reason=None,
            refreshed_instructions=instructions,
            output_schema_reminder=schema,
        )
