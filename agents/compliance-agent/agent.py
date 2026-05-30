"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class ComplianceAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="compliance-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield compliance agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("map_finding_to_controls", "map finding to controls", {"finding_id": {'type': 'string'}, "frameworks": {'type': 'array', 'items': {'type': 'string'}}}, ['finding_id', 'frameworks']),
            tool_schema("assess_control_coverage", "assess control coverage", {"client_id": {'type': 'string'}, "framework": {'type': 'string'}}, ['client_id', 'framework']),
            tool_schema("identify_gaps", "identify gaps", {"client_id": {'type': 'string'}, "framework": {'type': 'string'}}, ['client_id', 'framework']),
            tool_schema("generate_evidence_pack", "generate evidence pack", {"control_id": {'type': 'string'}, "client_id": {'type': 'string'}}, ['control_id', 'client_id']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "map_finding_to_controls":
            return await T.map_finding_to_controls(tool_input.get("finding_id", ""), tool_input.get("frameworks", []))
        if tool_name == "assess_control_coverage":
            return await T.map_finding_to_controls("finding-001", [tool_input.get("framework", "NIST")])
        if tool_name == "identify_gaps":
            return await T.map_finding_to_controls("gap-scan", [tool_input.get("framework", "NIST")])
        if tool_name == "generate_evidence_pack":
            return await T.map_finding_to_controls(tool_input.get("control_id", ""), [tool_input.get("client_id", self.tenant_id)])
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
