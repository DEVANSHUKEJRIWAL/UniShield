"""UniShield-SCR — Source Code Review agent."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.schemas.output_schema import SCRAgentOutput
from unishield.agents.scr.stages.stage1_acquisition import AcquisitionStage
from unishield.agents.scr.stages.stage2_detection import DetectionStage
from unishield.agents.scr.stages.stage3_analysis import AnalysisStage
from unishield.agents.scr.stages.stage7_ai_analysis import AIAnalysisStage
from unishield.agents.scr.stages.stage8_threat_intel import ThreatIntelStage
from unishield.agents.scr.stages.stage9_ranking import RankingStage
from unishield.agents.scr.stages.stage10_output import OutputStage
from unishield.config.settings import settings
from unishield.infrastructure.kafka_client import KafkaClient
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient
from unishield.openclaw.agent import Agent

logger = logging.getLogger(__name__)


class SCRAgent(Agent):
    """Source Code Review agent — static analysis, secrets, SBOM, AI enrichment."""

    name = "UniShield-SCR"
    version = "1.0.0"

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        shared_memory: SharedMemoryClient,
        kafka: KafkaClient,
    ) -> None:
        self._personal = personal_memory
        self._shared = shared_memory
        self._kafka = kafka
        self._acquisition = AcquisitionStage(personal_memory)
        self._detection = DetectionStage(personal_memory)
        self._analysis = AnalysisStage()
        self._ai = AIAnalysisStage(personal_memory)
        self._threat_intel = ThreatIntelStage(personal_memory, shared_memory)
        self._ranking = RankingStage(personal_memory)
        self._output = OutputStage(personal_memory, shared_memory, kafka, self.version)

    async def run(self, input: SCRAgentInput) -> SCRAgentOutput:
        scan_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        logger.info("Starting SCR scan %s for workflow %s", scan_id, input.workflow_id)

        files = await self._stage1_acquisition(scan_id, input)
        detection = await self._stage2_detection(scan_id, files)
        priority_files = self._build_priority_queue(files, input)
        await self._stage3_to_6_analysis(priority_files, scan_id, input, detection["rule_sets"])
        await self._stage7_ai_analysis(scan_id, input)
        await self._stage8_threat_intel(scan_id, input)
        ranked = await self._stage9_ranking(scan_id)
        files_scanned = len(await self._personal.get_files_scanned(scan_id))
        return await self._stage10_output(scan_id, ranked, input, started_at, files_scanned)

    async def _stage1_acquisition(self, scan_id: str, input: SCRAgentInput) -> list[str]:
        return await self._acquisition.run(scan_id, input)

    async def _stage2_detection(self, scan_id: str, files: list[str]) -> dict:
        return await self._detection.run(scan_id, files)

    def _build_priority_queue(self, files: list[str], input: SCRAgentInput) -> list[str]:
        def score(path: str) -> int:
            s = 0
            for jewel in input.crown_jewels:
                if jewel in path:
                    s += 100
            if input.diff_head and path in input.file_paths:
                s += 80
            for pattern in ("auth", "password", "crypto", "admin"):
                if pattern in path.lower():
                    s += 60
            for pattern in ("test/", "tests/", "vendor/", "node_modules/"):
                if pattern in path:
                    s -= 50
            return s

        return sorted(files, key=score, reverse=True)

    async def _stage3_to_6_analysis(
        self,
        files: list[str],
        scan_id: str,
        input: SCRAgentInput,
        rule_sets: dict,
    ) -> None:
        batch_size = settings.scr_batch_size
        batches = [
            files[i : i + batch_size]
            for i in range(0, len(files), batch_size)
        ]
        total_batches = len(batches) or 1

        progress = await self._personal.load_scan_progress(scan_id)
        completed: set[str] = set()
        if progress:
            completed = set(progress.get("completed_batches", []))

        for idx, batch_files in enumerate(batches):
            batch_id = f"batch-{idx}"
            if batch_id in completed:
                continue

            result = await self._analysis.process_batch(
                batch_id, batch_files, input, rule_sets
            )

            for finding in result.code_findings:
                fp = finding.get("fingerprint", "")
                if fp and await self._personal.fingerprint_exists(scan_id, fp):
                    continue
                if fp:
                    await self._personal.add_fingerprint(scan_id, fp)

            await self._personal.append_findings(
                scan_id,
                batch_id,
                result.code_findings,
                result.secret_findings,
                result.dependency_findings,
            )

            for fp in batch_files:
                await self._personal.save_file_scanned(scan_id, fp)

            completed.add(batch_id)
            await self._personal.save_scan_progress(
                scan_id,
                total_batches,
                list(completed),
                [],
                batch_id,
            )

    async def _stage7_ai_analysis(self, scan_id: str, input: SCRAgentInput) -> None:
        await self._ai.run(scan_id, input)

    async def _stage8_threat_intel(self, scan_id: str, input: SCRAgentInput) -> None:
        await self._threat_intel.run(scan_id, input)

    async def _stage9_ranking(self, scan_id: str):
        return await self._ranking.run(scan_id)

    async def _stage10_output(
        self,
        scan_id: str,
        ranked_findings: list,
        input: SCRAgentInput,
        started_at: datetime,
        files_scanned: int,
    ) -> SCRAgentOutput:
        return await self._output.run(
            scan_id, ranked_findings, input, started_at, files_scanned
        )
