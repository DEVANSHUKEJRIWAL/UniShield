"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class ReportingAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="reporting-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield reporting agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("gather_findings_summary", "gather findings summary", {"client_id": {'type': 'string'}, "period": {'type': 'string'}}, ['client_id', 'period']),
            tool_schema("generate_executive_summary", "generate executive summary", {"findings": {'type': 'string'}, "audience": {'type': 'string'}}, ['findings', 'audience']),
            tool_schema("generate_compliance_report", "generate compliance report", {"framework": {'type': 'string'}, "client_id": {'type': 'string'}}, ['framework', 'client_id']),
            tool_schema("export_pdf", "export pdf", {"report_content": {'type': 'string'}}, ['report_content']),
            tool_schema("schedule_report", "schedule report", {"config": {'type': 'string'}}, ['config']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "gather_findings_summary":
            return await T.gather_findings_summary(tool_input.get("client_id", ""), tool_input.get("period", []))
        if tool_name == "generate_executive_summary":
            return await T.gather_findings_summary(self.tenant_id)
        if tool_name == "generate_compliance_report":
            return await T.map_finding_to_controls("report", [tool_input.get("framework", "NIST")])
        if tool_name == "export_pdf":
            return await T.gather_findings_summary(self.tenant_id)
        if tool_name == "schedule_report":
            return await T.gather_findings_summary(self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
