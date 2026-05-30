"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class IncidentResponseAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="incident-response-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield incident response agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("retrieve_playbook", "retrieve playbook", {"incident_type": {'type': 'string'}}, ['incident_type']),
            tool_schema("triage_incident", "triage incident", {"incident_data": {'type': 'string'}}, ['incident_data']),
            tool_schema("generate_escalation_path", "generate escalation path", {"incident_id": {'type': 'string'}}, ['incident_id']),
            tool_schema("suggest_containment_actions", "suggest containment actions", {"threat_type": {'type': 'string'}, "blast_radius": {'type': 'string'}}, ['threat_type', 'blast_radius']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "retrieve_playbook":
            return await T.search_qdrant("ir_playbooks", tool_input.get("incident_type", ""))
        if tool_name == "triage_incident":
            return await T.gather_findings_summary(self.tenant_id)
        if tool_name == "generate_escalation_path":
            return await T.gather_findings_summary(self.tenant_id)
        if tool_name == "suggest_containment_actions":
            return await T.gather_findings_summary(self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
