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
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
