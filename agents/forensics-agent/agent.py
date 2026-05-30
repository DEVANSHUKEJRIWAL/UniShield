"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class ForensicsAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="forensics-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield forensics agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("extract_iocs", "extract iocs", {"text_or_log": {'type': 'string'}}, ['text_or_log']),
            tool_schema("reconstruct_timeline", "reconstruct timeline", {"incident_id": {'type': 'string'}, "events": {'type': 'array', 'items': {'type': 'string'}}}, ['incident_id', 'events']),
            tool_schema("analyse_artefact", "analyse artefact", {"artefact_type": {'type': 'string'}, "data": {'type': 'string'}}, ['artefact_type', 'data']),
            tool_schema("correlate_iocs_with_graph", "correlate iocs with graph", {"ioc_list": {'type': 'string'}}, ['ioc_list']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "extract_iocs":
            return await T.extract_iocs(tool_input.get("text_or_log", ""))
        if tool_name == "reconstruct_timeline":
            return await T.extract_iocs(str(tool_input.get("events", [])))
        if tool_name == "analyse_artefact":
            return await T.extract_iocs(str(tool_input.get("data", "")))
        if tool_name == "correlate_iocs_with_graph":
            return await T.traverse_attack_paths(tool_input.get("ioc_list", ["unknown"])[0], 5, self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle task with structured forensics finding in mock mode."""
        from agents._openclaw.structured import structured_on_event

        await structured_on_event(
            self,
            event,
            {"ioc_observed": self._emit_forensics, "forensics": self._emit_forensics},
        )

    async def _emit_forensics(self, payload: dict[str, Any]) -> None:
        from agents._openclaw import tools as T
        from agents._openclaw.structured import emit_mock_finding
        from packages.core.schemas import ForensicFinding

        text = str(payload.get("text_or_log", payload.get("indicator", "192.168.1.45 evil-c2.example.com")))
        iocs = await T.extract_iocs(text)
        finding = ForensicFinding(
            finding_id=__import__("uuid").uuid4().hex,
            tenant_id=self.tenant_id,
            agent_id=self.agent_name,
            type="forensics",
            severity="high" if iocs else "medium",
            confidence=0.86,
            title=f"Forensic IOC extraction ({len(iocs)} indicators)",
            description=f"Extracted {len(iocs)} IOCs from artefact analysis",
            reasoning_summary="Forensics structured handler",
            iocs=iocs,
            contributing_agents=[self.agent_name],
            recommended_actions=["Block malicious IOCs", "Expand hunt query"],
        )
        await self.emit_structured_finding(finding)
