"""Stage 8 — threat intel correlation with crown-jewel risk elevation."""

from __future__ import annotations

import logging

from backend.scr.schemas.input_schema import SCRAgentInput
from backend.memory.personal_memory import PersonalMemoryClient
from backend.memory.shared_memory import SharedMemoryClient

logger = logging.getLogger(__name__)

CROWN_JEWEL_RISK_BOOST = 25


class ThreatIntelStage:
    """Correlates findings with IOCs, TTPs, and crown jewel proximity."""

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        shared_memory: SharedMemoryClient,
    ) -> None:
        self._memory = personal_memory
        self._shared = shared_memory

    async def run(self, scan_id: str, input: SCRAgentInput) -> int:
        ioc_list = list(input.ioc_list)
        ttps = list(input.threat_actor_ttps)

        try:
            web_output = await self._shared.read_agent_output(input.workflow_id, "web")
        except Exception:
            try:
                web_output = await self._shared.read_agent_output(input.workflow_id, "UniShield-Web")
            except Exception:
                web_output = {}

        ioc_list.extend(web_output.get("ioc_list", []))
        ttps.extend(web_output.get("threat_actor_ttps", []))

        findings_data = await self._memory.load_all_findings(scan_id)
        enriched: list[dict] = []
        total_risk_boost = 0

        for finding in findings_data["code"]:
            if finding.get("suppressed"):
                continue
            snippet = finding.get("code_snippet", "")
            file_path = finding.get("file_path", "")
            risk_boost = int(finding.get("risk_boost", 0))

            for ioc in ioc_list:
                if ioc and ioc in snippet:
                    finding["severity"] = "CRITICAL"
                    finding["incident_relevance"] = True
                    finding["threat_actor_relevance"] = finding.get("threat_actor_relevance", []) + [ioc]
                    risk_boost += 15

            for ttp in ttps:
                if ttp and ttp.lower() in snippet.lower():
                    finding["severity"] = "CRITICAL"
                    finding["mitre_technique"] = ttp
                    finding["threat_actor_relevance"] = finding.get("threat_actor_relevance", []) + [ttp]
                    risk_boost += 10

            for jewel in input.crown_jewels:
                if jewel and jewel in file_path:
                    finding["crown_jewel_boost"] = True
                    sev = finding.get("severity", "LOW").upper()
                    if sev in ("LOW", "MEDIUM"):
                        finding["severity"] = "HIGH"
                    risk_boost += CROWN_JEWEL_RISK_BOOST

            finding["risk_boost"] = risk_boost
            total_risk_boost += risk_boost
            enriched.append(finding)

        if enriched:
            await self._memory.append_findings(scan_id, "threat_intel", enriched, [], [])

        logger.info("Threat intel stage processed %d findings (risk_boost=%d)", len(enriched), total_risk_boost)
        return total_risk_boost
