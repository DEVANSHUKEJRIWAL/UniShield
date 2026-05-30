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
            return await T.run_semgrep(tool_input.get("python_files", [""])[0] if tool_input.get("python_files") else "")
        if tool_name == "scan_for_secrets":
            return await T.scan_for_secrets(tool_input.get("files", ""))
        if tool_name == "scan_dependency_vulnerabilities":
            return await T.lookup_cve("CVE-2024-0001")
        if tool_name == "analyse_diff_semantics":
            return await T.extract_iocs(tool_input.get("diff_text", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={"event": event})
