"""SCR runner — coordinates 10-stage workflow via OpenClaw SDK."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from backend.orchestrator.action_gate import ActionGate

from backend.agents.skill_executor import execute_with_skill, parse_json_response
from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

from backend.scr.scr_callback import SCRCallbackHandler
from backend.scr.scr_prompt_builder import SCRPromptBuilder
from backend.scr.schemas.input_schema import SCRAgentInput
from backend.scr.schemas.output_schema import SCRAgentOutput
from backend.scr.stages.batch_context_guard import BatchContextGuard
from backend.scr.stages.findings_filter import FilterStats, FindingsFilter
from backend.scr.tools.repo_acquirer import AcquisitionResult
from backend.scr.stages.stage1_acquisition import AcquisitionStage
from backend.scr.stages.stage2_detection import DetectionStage
from backend.scr.stages.stage3_analysis import AnalysisStage
from backend.scr.stages.stage7_ai_analysis import AIAnalysisStage
from backend.scr.stages.stage8_threat_intel import ThreatIntelStage
from backend.scr.stages.stage9_ranking import RankingStage
from backend.scr.stages.stage10_output import OutputStage
from backend.scr.scr_progress import ScrProgressTracker
from backend.config.settings import Settings, settings
from backend.infrastructure.kafka_client import KafkaProducer
from backend.infrastructure.model_router import ModelRouter
from backend.memory.personal_memory import PersonalMemoryClient
from backend.memory.repo_memory import RepoMemoryClient
from backend.memory.shared_memory import AgentOutputNotReady, SharedMemoryClient
from backend.scr.tools.tool_requirements import validate_required_tools
from backend.scr.tools.scanner_integration import sbom_summary

logger = logging.getLogger(__name__)


def normalize_agent_key(agent_id: str) -> str:
    return agent_id.lower().replace("unishield-", "")


def _repo_scan_expected(input: SCRAgentInput) -> bool:
    return bool(input.repo_url) and not input.file_paths and not input.raw_code and not input.archive_path


def _empty_repo_scan_message(input: SCRAgentInput) -> str:
    if not input.repo_auth_token:
        return (
            "Repository scan is missing auth token — reconnect the repo with a valid PAT "
            "and retry the scan."
        )
    if not input.repo_ref:
        return (
            "Repository scan is missing branch/ref — set the default branch on the connection "
            "or pass ref_override."
        )
    return (
        "Repository acquisition returned 0 scannable files. Verify the token can read the repo, "
        "the branch/ref exists, and the repository contains supported source files."
    )


class SCRRunner:
    """Runs UniShield-SCR using OpenClaw SDK and local analysis stages."""

    VERSION = "2.0.0"

    def __init__(
        self,
        openclaw_config: ClientConfig,
        shared_memory: SharedMemoryClient,
        personal_memory: PersonalMemoryClient,
        kafka: KafkaProducer,
        app_settings: Settings | None = None,
        model_router: ModelRouter | None = None,
        progress_tracker: ScrProgressTracker | None = None,
        action_gate: "ActionGate | None" = None,
        repo_memory: RepoMemoryClient | None = None,
    ) -> None:
        self.openclaw_config = openclaw_config
        self.shared_memory = shared_memory
        self.personal_memory = personal_memory
        self.kafka = kafka
        self.settings = app_settings or settings
        self.model_router = model_router or ModelRouter(self.settings)
        self.progress = progress_tracker
        self.action_gate = action_gate
        self.repo_memory = repo_memory
        self.prompt_builder = SCRPromptBuilder()
        self._acquisition = AcquisitionStage(personal_memory)
        self._detection = DetectionStage(personal_memory)
        self._analysis = AnalysisStage()
        self._ai = AIAnalysisStage(personal_memory, self.model_router)
        self._threat_intel = ThreatIntelStage(personal_memory, shared_memory)
        self._ranking = RankingStage(personal_memory)
        self._output = OutputStage(personal_memory, shared_memory, kafka, self.VERSION)
        self._findings_filter = FindingsFilter(
            self.model_router,
            use_ai_filtering=self.settings.scr_use_ai_fp_filter,
        )

    @asynccontextmanager
    async def _scr_agent_session(
        self,
        workflow_id: str,
        callback: SCRCallbackHandler,
    ) -> AsyncIterator[object | None]:
        """Yield an OpenClaw SCR agent, or None if the live gateway is unavailable."""
        connect_kwargs = {
            "gateway_ws_url": self.openclaw_config.gateway_ws_url,
            "api_key": self.openclaw_config.api_key,
            "mock_mode": self.openclaw_config.mock_mode,
            "callbacks": [callback],
        }
        if self.openclaw_config.mock_mode:
            async with OpenClawClient.connect(**connect_kwargs) as client:
                yield client.get_agent("unishield-scr", session_name=workflow_id)
            return
        if self.settings.scr_execution_mode == "local":
            yield None
            return
        try:
            async with OpenClawClient.connect(**connect_kwargs) as client:
                yield client.get_agent("unishield-scr", session_name=workflow_id)
        except Exception as exc:
            if self.settings.scr_execution_mode == "skill":
                raise RuntimeError(f"OpenClaw gateway required for skill mode: {exc}") from exc
            logger.warning(
                "OpenClaw gateway unavailable for workflow %s — continuing with local SCR tools: %s",
                workflow_id,
                exc,
            )
            yield None

    async def run(self, input: SCRAgentInput) -> SCRAgentOutput:
        """Run SCR — skill-first by default; local mode uses tools without OpenClaw."""
        if self.settings.scr_execution_mode == "local":
            from backend.scr.scr_tool_host import SCRToolHost

            host = SCRToolHost(self, input)
            return await host.run_canonical_sequence()

        from backend.scr.scr_skill_executor import SCRSkillExecutor

        return await SCRSkillExecutor(self).run(input)

    def _sort_by_priority(self, files: list[str], input: SCRAgentInput) -> list[str]:
        def score(path: str) -> int:
            s = 0
            for jewel in input.crown_jewels:
                if jewel in path:
                    s += 100
            if input.diff_head and path in input.file_paths:
                s += 80
            for kw in ("payment", "auth", "crypto", "swift"):
                if kw in path.lower():
                    s += 60
            for ext in (".env", ".pem", ".key"):
                if path.endswith(ext):
                    s += 40
            for prefix in ("test/", "tests/", "vendor/", "node_modules/"):
                if prefix in path:
                    s -= 50
            return s

        return sorted(files, key=score, reverse=True)

    async def _load_shared_context(self, input: SCRAgentInput) -> dict:
        try:
            return await self.shared_memory.read_agent_output(input.workflow_id, "web")
        except AgentOutputNotReady:
            return {}

    def _fingerprint(self, finding: dict) -> str:
        key = f"{finding.get('file_path')}:{finding.get('line_start')}:{finding.get('category')}"
        return hashlib.sha256(key.encode()).hexdigest()
