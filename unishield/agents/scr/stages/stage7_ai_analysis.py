"""Stage 7 — AI semantic analysis enrichment via ModelRouter."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.tools.scanner_integration import bfsi_context_boost
from unishield.config.settings import settings
from unishield.infrastructure.model_router import ModelRouter, TaskType
from unishield.memory.personal_memory import PersonalMemoryClient

logger = logging.getLogger(__name__)


class AIEnrichment(BaseModel):
    ai_explanation: str = ""
    ai_attack_scenario: str = ""
    ai_business_impact: str = ""
    ai_fix: str = ""
    ai_fix_code: str = ""
    false_positive_score: float = 0.0


class AIAnalysisStage:
    """Enriches HIGH+ findings with LLM-generated context; suppresses high FP scores."""

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        model_router: ModelRouter | None = None,
    ) -> None:
        self._memory = personal_memory
        self._router = model_router or ModelRouter(settings)
        self._concurrency = settings.scr_ai_concurrency
        self.models_used: list[str] = []

    async def run(self, scan_id: str, input: SCRAgentInput) -> list[str]:
        if not input.enable_ai_analysis:
            logger.info("Stage 7 skipped — enable_ai_analysis=false")
            return []

        if not (
            self._router._settings.anthropic_api_key
            or self._router._settings.openai_api_key
            or self._router._settings.google_api_key
        ):
            logger.warning(
                "AI enrichment disabled — set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable Stage 7"
            )

        findings_data = await self._memory.load_all_findings(scan_id)
        high_findings = [
            f
            for f in findings_data["code"]
            if f.get("severity", "").upper() in ("CRITICAL", "HIGH")
            and float(f.get("false_positive_score", 0)) <= 0.6
        ]

        semaphore = asyncio.Semaphore(self._concurrency)
        suppressed: list[dict] = []
        kept: list[dict] = []

        async def enrich(finding: dict) -> None:
            async with semaphore:
                enrichment = await self._enrich_finding(finding, input)
                finding.update(enrichment)
                await self._memory.increment_token_budget(scan_id, 800)
                if enrichment.get("false_positive_score", 0) > 0.6:
                    finding["suppressed"] = True
                    finding["suppression_reason"] = "AI false_positive_score > 0.6"
                    suppressed.append(finding)
                else:
                    kept.append(finding)

        await asyncio.gather(*[enrich(f) for f in high_findings])
        if high_findings:
            await self._memory.append_findings(scan_id, "ai_enriched", kept, [], [])
        logger.info(
            "AI analysis enriched %d findings (%d suppressed)",
            len(kept),
            len(suppressed),
        )
        return self.models_used

    async def _enrich_finding(self, finding: dict, input: SCRAgentInput) -> dict[str, Any]:
        bfsi = bfsi_context_boost(finding.get("file_path", ""), finding.get("code_snippet", ""))
        prompt = (
            f"Analyze this security finding for a BFSI client.\n"
            f"File: {finding.get('file_path')}\n"
            f"Severity: {finding.get('severity')}\n"
            f"Category: {finding.get('category')}\n"
            f"CWE: {finding.get('cwe_id')}\n"
            f"Snippet:\n{finding.get('code_snippet', '')}\n"
            f"BFSI heightened scrutiny: {bfsi}\n"
            f"Provide explanation, attack scenario, business impact, fix guidance, "
            f"optional fix code snippet, and false_positive_score (0-1)."
        )
        try:
            raw = await self._router.complete(
                TaskType.CODE_ANALYSIS,
                prompt,
                output_schema=AIEnrichment,
                max_tokens=1024,
            )
            data = json.loads(raw)
            enrichment = AIEnrichment.model_validate(data)
            self.models_used.append("model-router")
            return enrichment.model_dump()
        except Exception as exc:
            logger.debug("LLM enrichment fallback for %s: %s", finding.get("file_path"), exc)
            return self._template_enrichment(finding, bfsi)

    @staticmethod
    def _template_enrichment(finding: dict, bfsi: bool) -> dict[str, Any]:
        category = finding.get("category", "security")
        path = finding.get("file_path", "unknown")
        impact = (
            "Payment/transaction integrity risk — potential regulatory breach (PCI-DSS, SOX)."
            if bfsi
            else "Data breach risk affecting customer trust and operational continuity."
        )
        return {
            "ai_explanation": f"Potential {category} vulnerability detected in {path}.",
            "ai_attack_scenario": "An attacker could chain this weakness with adjacent controls gaps to exfiltrate data or execute unauthorized actions.",
            "ai_business_impact": impact,
            "ai_fix": "Apply defense-in-depth: validate inputs, use parameterized APIs, enforce least privilege, and add monitoring.",
            "ai_fix_code": "",
            "false_positive_score": 0.2,
        }
