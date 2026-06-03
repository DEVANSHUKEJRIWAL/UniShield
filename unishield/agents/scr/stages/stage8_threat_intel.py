"""Stage 8 — threat intel correlation."""

from __future__ import annotations

import logging

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.memory.personal_memory import PersonalMemoryClient
from unishield.memory.shared_memory import SharedMemoryClient

logger = logging.getLogger(__name__)


class ThreatIntelStage:
    """Correlates findings with IOCs, TTPs, and crown jewel proximity."""

    def __init__(
        self,
        personal_memory: PersonalMemoryClient,
        shared_memory: SharedMemoryClient,
    ) -> None:
        self._memory = personal_memory
        self._shared = shared_memory

    async def run(self, scan_id: str, input: SCRAgentInput) -> None:
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

        for finding in findings_data["code"]:
            snippet = finding.get("code_snippet", "")
            file_path = finding.get("file_path", "")

            for ioc in ioc_list:
                if ioc and ioc in snippet:
                    finding["severity"] = "CRITICAL"
                    finding["incident_relevance"] = True
                    finding["threat_actor_relevance"] = finding.get("threat_actor_relevance", []) + [ioc]

            for ttp in ttps:
                if ttp and ttp.lower() in snippet.lower():
                    finding["severity"] = "CRITICAL"
                    finding["mitre_technique"] = ttp
                    finding["threat_actor_relevance"] = finding.get("threat_actor_relevance", []) + [ttp]

            for jewel in input.crown_jewels:
                if jewel and jewel in file_path:
                    sev = finding.get("severity", "LOW").upper()
                    if sev in ("LOW", "MEDIUM"):
                        finding["severity"] = "HIGH"

            enriched.append(finding)

        if enriched:
            await self._memory.append_findings(scan_id, "threat_intel", enriched, [], [])

        logger.info("Threat intel stage processed %d findings", len(enriched))
