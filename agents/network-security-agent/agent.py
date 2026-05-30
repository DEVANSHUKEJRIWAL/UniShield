"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class NetworkSecurityAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="network-security-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield network security agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("analyse_port_scan_result", "analyse port scan result", {"nmap_output": {'type': 'string'}}, ['nmap_output']),
            tool_schema("detect_traffic_anomaly", "detect traffic anomaly", {"flow_data": {'type': 'string'}, "baseline": {'type': 'string'}}, ['flow_data', 'baseline']),
            tool_schema("recommend_firewall_rules", "recommend firewall rules", {"finding": {'type': 'string'}}, ['finding']),
            tool_schema("check_lateral_movement_indicators", "check lateral movement indicators", {"ip": {'type': 'string'}, "time_range": {'type': 'string'}}, ['ip', 'time_range']),
            tool_schema("query_knowledge_graph", "query knowledge graph", {"cypher": {'type': 'string'}}, ['cypher']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "analyse_port_scan_result":
            return await T.extract_iocs(tool_input.get("nmap_output", ""))
        if tool_name == "detect_traffic_anomaly":
            return await T.traverse_attack_paths(tool_input.get("ip", "unknown"), 3, self.tenant_id)
        if tool_name == "recommend_firewall_rules":
            return await T.traverse_attack_paths(tool_input.get("ip", "unknown"), 3, self.tenant_id)
        if tool_name == "check_lateral_movement_indicators":
            return await T.traverse_attack_paths(tool_input.get("ip", "unknown"), 3, self.tenant_id)
        if tool_name == "query_knowledge_graph":
            return await T.query_knowledge_graph(tool_input.get("cypher", ""), self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
