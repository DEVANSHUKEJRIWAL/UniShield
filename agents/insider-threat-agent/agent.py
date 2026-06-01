"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class InsiderThreatAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="insider-threat-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield insider threat agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("score_user_anomaly", "score user anomaly", {"user_id": {'type': 'string'}, "events": {'type': 'array', 'items': {'type': 'string'}}}, ['user_id', 'events']),
            tool_schema("detect_anomalous_access", "detect anomalous access", {"user_id": {'type': 'string'}, "access_logs": {'type': 'string'}}, ['user_id', 'access_logs']),
            tool_schema("check_privilege_escalation", "check privilege escalation", {"user_id": {'type': 'string'}}, ['user_id']),
            tool_schema("get_user_baseline", "get user baseline", {"user_id": {'type': 'string'}}, ['user_id']),
            tool_schema("retrieve_insider_patterns", "retrieve insider patterns", {"description": {'type': 'string'}}, ['description']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "score_user_anomaly":
            return await T.score_user_anomaly(tool_input.get("user_id", ""), tool_input.get("events", []))
        if tool_name == "detect_anomalous_access":
            return await T.score_user_anomaly(tool_input.get("user_id", ""), tool_input.get("access_logs", []))
        if tool_name == "check_privilege_escalation":
            return await T.score_user_anomaly(tool_input.get("user_id", ""), [{"type": "privilege_change"}])
        if tool_name == "get_user_baseline":
            return await T.get_user_baseline(tool_input.get("user_id", ""), self.tenant_id)
        if tool_name == "retrieve_insider_patterns":
            return await T.search_qdrant("insider_patterns", tool_input.get("description", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle task from Redis stream with structured message protocol."""
        from agents._openclaw.structured import mock_mode, parse_task_event

        payload, kg_context = parse_task_event(event)
        event_type = str(payload.get("type", ""))

        if event_type in ("anomalous_login", "insider_risk", "insider_scan") and mock_mode():
            await self._emit_insider_finding(payload)
            return
        await self.reason(__import__("json").dumps(payload), kg_context=kg_context)

    async def _emit_insider_finding(self, payload: dict[str, Any]) -> None:
        """Structured UEBA finding via Phase 2 insider scan pipeline."""
        from agents._openclaw import tools as T
        from packages.core.bfsi import BFSIFinding, bfsi_to_agent_finding
        from packages.core.persistence import upsert_insider_baseline
        from packages.phase2.insider import run_insider_scan

        user_id = str(payload.get("user_id", "unknown-user"))
        events = payload.get(
            "events",
            [
                {
                    "type": "login",
                    "timestamp": "2024-11-01T23:00:00Z",
                    "country": "RU",
                    "user_id": user_id,
                },
                {"type": "privilege_change", "user_id": user_id},
            ],
        )
        if isinstance(events, str):
            events = [{"type": events}]
        org = payload.get("org", self.tenant_id)
        industry = payload.get("industry", "banking")
        result = await run_insider_scan(org, industry, user_id, events if isinstance(events, list) else [], self.tenant_id)
        raw_findings = result.get("findings", [])
        if raw_findings:
            top = BFSIFinding.model_validate(raw_findings[0])
            finding = bfsi_to_agent_finding(top, self.tenant_id, self.agent_name, finding_type="insider_threat")
            finding.mitre_ttps_matched = ["T1078"]
            finding.raw = {"phase2": result}
            await self.emit_structured_finding(finding)
            return

        score = await T.score_user_anomaly(user_id, events if isinstance(events, list) else [])
        baseline = await T.get_user_baseline(user_id, self.tenant_id)
        await upsert_insider_baseline(
            self.tenant_id,
            user_id,
            {"window30d": baseline.get("window30d", {}), "window60d": baseline.get("window60d", {})},
            peer_group=str(score.get("peer_group", baseline.get("peer_group", "default"))),
        )
        from agents._openclaw.structured import emit_mock_finding

        await emit_mock_finding(
            self,
            payload,
            title=f"Insider risk: anomalous activity for {user_id}",
            severity=str(score.get("severity", "high")),
            confidence=0.87 if score.get("anomalous") else 0.72,
            description=f"Risk score {score.get('riskScore', 0)} — rules: {', '.join(score.get('triggeredRules', []))}",
            finding_type="insider_threat",
            mitre_ttps=["T1078"],
            recommended_actions=["Review access logs", "Verify with user manager", "Enable step-up MFA"],
        )
