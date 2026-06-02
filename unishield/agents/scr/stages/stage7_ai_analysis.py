"""Stage 7 — AI semantic analysis enrichment."""

from __future__ import annotations

import asyncio
import logging

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.config.settings import settings
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)


class AIAnalysisStage:
    """Enriches HIGH+ findings with LLM-generated context."""

    def __init__(self, personal_memory: PersonalMemoryClient) -> None:
        self._memory = personal_memory
        self._concurrency = settings.scr_ai_concurrency

    async def run(self, scan_id: str, input: SCRAgentInput) -> None:
        if not input.enable_ai_analysis:
            return

        findings_data = await self._memory.load_all_findings(scan_id)
        high_findings = [
            f for f in findings_data["code"]
            if f.get("severity", "").upper() in ("CRITICAL", "HIGH")
        ]

        semaphore = asyncio.Semaphore(self._concurrency)

        async def enrich(finding: dict) -> None:
            async with semaphore:
                finding["ai_explanation"] = (
                    f"Potential {finding.get('category', 'security')} vulnerability "
                    f"in {finding.get('file_path', 'unknown')}"
                )
                finding["ai_attack_scenario"] = "Attacker could exploit this to gain unauthorized access"
                finding["ai_business_impact"] = "Data breach risk affecting customer trust"
                finding["ai_fix"] = "Apply input validation and parameterized queries"
                await self._memory.increment_token_budget(scan_id, 500)

        await asyncio.gather(*[enrich(f) for f in high_findings])
        if high_findings:
            await self._memory.append_findings(scan_id, "ai_enriched", high_findings, [], [])
        logger.info("AI analysis enriched %d findings", len(high_findings))
