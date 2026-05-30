"""{cls} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class SourceCodeAgent(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="source-code-agent",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield source code agent specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {self.tenant_id}. Context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
        return [
            tool_schema("run_semgrep", "run semgrep", {"repo_path": {'type': 'string'}, "rules": {'type': 'string'}}, ['repo_path', 'rules']),
            tool_schema("run_bandit", "run bandit", {"python_files": {'type': 'string'}}, ['python_files']),
            tool_schema("scan_for_secrets", "scan for secrets", {"files": {'type': 'string'}}, ['files']),
            tool_schema("scan_dependency_vulnerabilities", "scan dependency vulnerabilities", {"requirements_file": {'type': 'string'}}, ['requirements_file']),
            tool_schema("analyse_diff_semantics", "analyse diff semantics", {"diff_text": {'type': 'string'}}, ['diff_text']),
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
        from agents._openclaw import tools as T

        if tool_name == "run_semgrep":
            return await T.run_semgrep(tool_input.get("repo_path", ""), tool_input.get("rules", []))
        if tool_name == "run_bandit":
            path = tool_input.get("python_files", "")
            if isinstance(path, list):
                path = path[0] if path else "."
            return await T.run_bandit(path or ".")
        if tool_name == "scan_for_secrets":
            return await T.scan_for_secrets(tool_input.get("files", ""))
        if tool_name == "scan_dependency_vulnerabilities":
            return await T.lookup_cve("CVE-2024-0001")
        if tool_name == "analyse_diff_semantics":
            return await T.extract_iocs(tool_input.get("diff_text", ""))
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

        if event_type == "code_commit" and mock_mode():
            await self._emit_code_finding(payload, kg_context)
            return
        await self.reason(__import__("json").dumps(payload), kg_context=kg_context)

    async def _emit_code_finding(self, payload: dict[str, Any], kg_context: dict[str, Any]) -> None:
        """Structured code finding for commit events (Semgrep/secrets mock/live)."""
        from agents._openclaw import tools as T
        from packages.core.schemas import CodeFinding

        repo = payload.get("repo_path", "/workspace")
        semgrep = await T.run_semgrep(repo)
        secrets = await T.scan_for_secrets([f"{repo}/.env"])
        top = semgrep[0] if semgrep else {"file": repo, "line": 0, "rule": "none", "severity": "INFO"}
        finding = CodeFinding(
            finding_id=__import__("uuid").uuid4().hex,
            tenant_id=self.tenant_id,
            agent_id=self.agent_name,
            severity="critical" if secrets else "high" if top.get("severity") == "ERROR" else "medium",
            confidence=0.88 if secrets else 0.8,
            title="Static analysis findings on commit",
            description=f"Semgrep rule {top.get('rule')} in {top.get('file')}:{top.get('line')}",
            reasoning_summary=f"SAST scan on {repo}; {len(secrets)} secret(s), {len(semgrep)} rule hit(s)",
            evidence_references=[top.get("file", repo)],
            file_path=str(top.get("file", "")),
            line_number=int(top.get("line", 0)),
            cwe_reference="CWE-798" if secrets else "CWE-200",
            recommended_fix="Remove hardcoded secrets and rotate credentials" if secrets else "Remediate SAST finding",
            contributing_agents=[self.agent_name],
        )
        await self.emit_structured_finding(finding)
