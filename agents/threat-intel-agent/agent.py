"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class ThreatIntelAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="threat-intel-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield threat intel agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("query_virustotal", "query virustotal", {"indicator": {'type': 'string'}}, ['indicator']),
            tool_schema("query_shodan", "query shodan", {"ip": {'type': 'string'}}, ['ip']),
            tool_schema("lookup_mitre_attack", "lookup mitre attack", {"technique_id": {'type': 'string'}}, ['technique_id']),
            tool_schema("search_threat_intel_corpus", "search threat intel corpus", {"query": {'type': 'string'}}, ['query']),
            tool_schema("correlate_iocs", "correlate iocs", {"ioc_list": {'type': 'string'}}, ['ioc_list']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "query_virustotal":
            return await T.query_virustotal(tool_input.get("indicator", ""))
        if tool_name == "query_shodan":
            return await T.query_shodan(tool_input.get("ip", ""))
        if tool_name == "lookup_mitre_attack":
            return await T.search_qdrant("threat_intel", tool_input.get("technique_id", ""))
        if tool_name == "search_threat_intel_corpus":
            return await T.search_qdrant("threat_intel", tool_input.get("query", ""))
        if tool_name == "correlate_iocs":
            return await T.extract_iocs(", ".join(tool_input.get("ioc_list", [])))
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
