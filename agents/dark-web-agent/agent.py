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
            return await T.detect_typosquatting(tool_input.get("domain", ""))
        if tool_name == "lookup_threat_actor":
            return await T.search_qdrant("threat_intel", tool_input.get("name_or_alias", ""))
        if tool_name == "query_knowledge_graph":
            return await T.query_knowledge_graph(tool_input.get("cypher", ""), self.tenant_id)
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle task from Redis stream with structured message protocol."""
        from packages.core.agent_messages import AgentTaskMessage

        try:
            task = AgentTaskMessage.from_redis(event)
            kg_context = task.kg_context()
            payload = task.input
        except ValueError:
            kg_context = {"event": event}
            payload = event

        event_type = str(payload.get("type", ""))
        from agents._openclaw.structured import mock_mode

        if event_type in ("credential_leak", "darkweb_scan") and mock_mode():
            await self._emit_credential_finding(payload)
            return
        await self.reason(__import__("json").dumps(payload), kg_context=kg_context)

    async def _emit_credential_finding(self, payload: dict[str, Any]) -> None:
        """Structured breach finding via Phase 2 dark web pipeline."""
        from packages.core.bfsi import BFSIFinding, bfsi_to_agent_finding
        from packages.core.schemas import BreachFinding, CredentialExposureAlert
        from packages.phase2.dark_web import run_dark_web_scan

        domain = payload.get("domain") or payload.get("email_domain") or "meridian.com"
        brand = payload.get("brand") or domain.split(".")[0]
        industry = payload.get("industry", "banking")
        result = await run_dark_web_scan(domain, brand, industry, self.tenant_id)
        raw_findings = result.get("findings", [])
        if raw_findings:
            top = BFSIFinding.model_validate(raw_findings[0])
            finding = bfsi_to_agent_finding(top, self.tenant_id, self.agent_name, finding_type="breach")
            finding.raw = {"phase2": result}
            await self.emit_structured_finding(finding)
            return

        from agents._openclaw import tools as T

        exposure = await T.check_credential_exposure(domain)
        alert = CredentialExposureAlert.from_tool_result(exposure)
        finding = BreachFinding(
            finding_id=__import__("uuid").uuid4().hex,
            tenant_id=self.tenant_id,
            agent_id=self.agent_name,
            severity=alert.severity,
            confidence=alert.confidence,
            title=f"Credential exposure detected for {domain}",
            description=alert.summary,
            reasoning_summary=f"Dark web credential check via {alert.source}",
            evidence_references=[alert.source],
            affected_entities=alert.affected_identities,
            contributing_agents=[self.agent_name],
            recommended_actions=["Force password reset", "Enable MFA", "Review privileged accounts"],
            raw={"phase2": result},
        )
        await self.emit_structured_finding(finding)
