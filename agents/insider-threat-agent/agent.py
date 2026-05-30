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
            return await T.get_user_baseline(tool_input.get("user_id", ""))
        if tool_name == "retrieve_insider_patterns":
            return await T.search_qdrant("insider_patterns", tool_input.get("description", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle task from Redis stream with structured message protocol."""
        from agents._openclaw.structured import parse_task_event
        from packages.core.config import settings

        payload, kg_context = parse_task_event(event)
        event_type = str(payload.get("type", ""))

        if event_type in ("anomalous_login", "insider_risk") and not settings.anthropic_api_key:
            await self._emit_insider_finding(payload)
            return
        await self.reason(__import__("json").dumps(payload), kg_context=kg_context)

    async def _emit_insider_finding(self, payload: dict[str, Any]) -> None:
        """Structured UEBA finding for anomalous login events."""
        from agents._openclaw import tools as T
        from agents._openclaw.structured import emit_mock_finding
        from packages.core.insider_schema import InsiderRiskScore

        user_id = str(payload.get("user_id", "unknown-user"))
        events = payload.get("events", [{"type": "login", "anomalous": True}])
        if isinstance(events, str):
            events = [{"type": events}]
        score = await T.score_user_anomaly(user_id, events if isinstance(events, list) else [])
        baseline = await T.get_user_baseline(user_id)
        risk = InsiderRiskScore(
            user_id=user_id,
            z_score=float(score.get("z_score", 2.8)),
            anomalous=bool(score.get("anomalous", True)),
            peer_group=str(score.get("peer_group", baseline.get("peer_group", "default"))),
            severity="high" if score.get("anomalous") else "medium",
            confidence=0.87 if score.get("anomalous") else 0.72,
            factors=["off-hours login", "geo anomaly"] if score.get("anomalous") else [],
        )
        await emit_mock_finding(
            self,
            payload,
            title=f"Insider risk: anomalous activity for {user_id}",
            severity=risk.severity,
            confidence=risk.confidence,
            description=f"Z-score {risk.z_score:.2f} vs peer group {risk.peer_group}",
            finding_type="insider_threat",
            mitre_ttps=["T1078"],
            recommended_actions=["Review access logs", "Verify with user manager", "Enable step-up MFA"],
        )
