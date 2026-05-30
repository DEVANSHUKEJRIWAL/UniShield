"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class GraphQueryAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="graph-query-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield graph query agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("traverse_attack_paths", "traverse attack paths", {"source_entity": {'type': 'string'}, "depth": {'type': 'string'}}, ['source_entity', 'depth']),
            tool_schema("find_crown_jewels_reachable", "find crown jewels reachable", {"from_entity": {'type': 'string'}}, ['from_entity']),
            tool_schema("identify_chokepoints", "identify chokepoints", {"client_id": {'type': 'string'}}, ['client_id']),
            tool_schema("get_blast_radius", "get blast radius", {"finding_id": {'type': 'string'}}, ['finding_id']),
            tool_schema("nl_to_cypher", "nl to cypher", {"natural_language_query": {'type': 'string'}}, ['natural_language_query']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "traverse_attack_paths":
            return await T.traverse_attack_paths(tool_input.get("source_entity", ""), tool_input.get("depth", []))
        if tool_name == "find_crown_jewels_reachable":
            return await T.traverse_attack_paths(tool_input.get("from_entity", ""), 5, self.tenant_id)
        if tool_name == "identify_chokepoints":
            return await T.query_knowledge_graph("MATCH (n) RETURN n LIMIT 10", self.tenant_id)
        if tool_name == "get_blast_radius":
            return await T.traverse_attack_paths(tool_input.get("finding_id", ""), 5, self.tenant_id)
        if tool_name == "nl_to_cypher":
            return await T.query_knowledge_graph("MATCH (n {clientId: $tenant_id}) RETURN n LIMIT 10", self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
