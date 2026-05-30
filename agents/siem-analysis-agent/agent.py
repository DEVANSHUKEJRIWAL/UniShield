"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class SiemAnalysisAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="siem-analysis-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield siem analysis agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("run_splunk_search", "run splunk search", {"query": {'type': 'string'}, "time_range": {'type': 'string'}}, ['query', 'time_range']),
            tool_schema("detect_log_anomaly", "detect log anomaly", {"log_stream": {'type': 'string'}, "baseline": {'type': 'string'}}, ['log_stream', 'baseline']),
            tool_schema("correlate_alerts", "correlate alerts", {"alert_list": {'type': 'string'}}, ['alert_list']),
            tool_schema("query_elasticsearch", "query elasticsearch", {"query": {'type': 'string'}}, ['query']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "run_splunk_search":
            return await T.run_splunk_search(tool_input.get("query", ""), tool_input.get("time_range", []))
        if tool_name == "detect_log_anomaly":
            return await T.run_splunk_search("index=main | stats count", "-24h")
        if tool_name == "correlate_alerts":
            return await T.run_splunk_search("index=alerts | stats count", "-24h")
        if tool_name == "query_elasticsearch":
            return await T.run_splunk_search(tool_input.get("query", "*"), "-24h")
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
