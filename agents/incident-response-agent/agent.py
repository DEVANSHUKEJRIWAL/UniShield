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
        """Handle task with structured IR finding in mock mode."""
        from agents._openclaw.structured import structured_on_event

        await structured_on_event(
            self,
            event,
            {
                "credential_leak": self._emit_ir,
                "siem_alert": self._emit_ir,
                "incident": self._emit_ir,
            },
        )

    async def _emit_ir(self, payload: dict[str, Any]) -> None:
        from agents._openclaw import tools as T
        from packages.core.schemas import IRFinding

        incident_type = str(payload.get("type", "incident"))
        playbook = await T.search_qdrant("ir_playbooks", incident_type)
        finding = IRFinding(
            finding_id=__import__("uuid").uuid4().hex,
            tenant_id=self.tenant_id,
            agent_id=self.agent_name,
            type="incident_response",
            severity=str(payload.get("severity", "high")),
            confidence=0.84,
            title=f"IR triage: {incident_type}",
            description=f"Playbook retrieved; {len(playbook)} reference(s)",
            reasoning_summary="Incident response structured handler",
            playbook_reference=incident_type,
            priority_actions=["Isolate affected hosts", "Preserve forensic evidence", "Notify CISO"],
            contributing_agents=[self.agent_name],
        )
        await self.emit_structured_finding(finding)
