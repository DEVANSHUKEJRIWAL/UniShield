"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class DarkWebAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="dark-web-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield dark web agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("crawl_dark_web_feeds", "crawl dark web feeds", {"query": {'type': 'string'}, "sources": {'type': 'string'}}, ['query', 'sources']),
            tool_schema("check_credential_exposure", "check credential exposure", {"email_domain": {'type': 'string'}}, ['email_domain']),
            tool_schema("monitor_paste_sites", "monitor paste sites", {"keywords": {'type': 'string'}}, ['keywords']),
            tool_schema("detect_typosquatting", "detect typosquatting", {"domain": {'type': 'string'}}, ['domain']),
            tool_schema("lookup_threat_actor", "lookup threat actor", {"name_or_alias": {'type': 'string'}}, ['name_or_alias']),
            tool_schema("query_knowledge_graph", "query knowledge graph", {"cypher": {'type': 'string'}}, ['cypher']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "crawl_dark_web_feeds":
            return await T.crawl_dark_web_feeds(tool_input.get("query", ""), tool_input.get("sources", []))
        if tool_name == "check_credential_exposure":
            return await T.check_credential_exposure(tool_input.get("email_domain", ""))
        if tool_name == "monitor_paste_sites":
            return await T.crawl_dark_web_feeds(tool_input.get("keywords", ""), ["paste"])
        if tool_name == "detect_typosquatting":
            return await T.check_credential_exposure(tool_input.get("domain", ""))
        if tool_name == "lookup_threat_actor":
            return await T.search_qdrant("threat_intel", tool_input.get("name_or_alias", ""))
        if tool_name == "query_knowledge_graph":
            return await T.query_knowledge_graph(tool_input.get("cypher", ""), self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
