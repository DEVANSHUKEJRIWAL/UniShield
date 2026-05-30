#!/usr/bin/env python3
"""Generate agent stub files for all UniShield agents."""

from pathlib import Path

AGENTS: dict[str, str] = {
    "orchestrator": "Central task router using LangGraph for multi-agent dispatch.",
    "dark-web-agent": "Monitor dark web forums, paste sites, and breach databases.",
    "source-code-agent": "AI-powered static analysis on PRs and repos.",
    "insider-threat-agent": "Detect insider threats via UEBA and anomaly detection.",
    "threat-intel-agent": "Query external threat intelligence sources.",
    "vulnerability-agent": "CVE lookup, CVSS scoring, and patch prioritisation.",
    "incident-response-agent": "Playbook retrieval, triage, and escalation.",
    "siem-analysis-agent": "Log pattern analysis and alert correlation.",
    "network-security-agent": "Port scan analysis and traffic anomaly detection.",
    "compliance-agent": "Control mapping and regulatory evidence collection.",
    "forensics-agent": "IOC extraction and timeline reconstruction.",
    "graph-query-agent": "Natural-language interface to the Neo4j knowledge graph.",
    "reporting-agent": "Synthesise findings into multi-audience reports.",
}


def class_name(agent_dir: str) -> str:
    """Convert agent directory name to PascalCase class name."""
    parts = agent_dir.replace("-agent", "").split("-")
    return "".join(p.capitalize() for p in parts) + "Agent"


def main() -> None:
    """Generate stub files for each agent."""
    root = Path(__file__).parent.parent / "agents"
    for agent_dir, description in AGENTS.items():
        agent_path = root / agent_dir
        agent_path.mkdir(parents=True, exist_ok=True)
        prompts_path = agent_path / "prompts"
        prompts_path.mkdir(exist_ok=True)

        cls = class_name(agent_dir)
        module_name = agent_dir.replace("-", "_")

        (agent_path / "__init__.py").write_text(
            f'"""{description}"""\n\nfrom agents.{module_name}.agent import {cls}\n\n__all__ = ["{cls}"]\n'
        )

        (agent_path / "agent.py").write_text(
            f'"""{cls} implementation."""\n\n'
            f"from typing import Any\n\n"
            f"from agents._openclaw.base import OpenClawAgent\n\n\n"
            f"class {cls}(OpenClawAgent):\n"
            f'    """{description}"""\n\n'
            f"    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:\n"
            f"        super().__init__(\n"
            f"            agent_id=agent_id,\n"
            f'            agent_name="{agent_dir}",\n'
            f"            tenant_id=tenant_id,\n"
            f"            **kwargs,\n"
            f"        )\n\n"
            f"    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:\n"
            f'        """Return system prompt with KG context."""\n'
            f"        return (\n"
            f'            f"You are the UniShield {agent_dir.replace("-", " ")} agent. "\n'
            f'            f"Tenant: {{self.tenant_id}}. Context: {{kg_context}}"\n'
            f"        )\n\n"
            f"    async def get_tools(self) -> list[dict[str, Any]]:\n"
            f'        """Return Anthropic tool schemas."""\n'
            f"        return []\n\n"
            f"    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:\n"
            f'        """Execute a tool call."""\n'
            f'        return {{"error": f"Tool {{tool_name}} not yet implemented"}}\n\n'
            f"    async def on_event(self, event: dict[str, Any]) -> None:\n"
            f'        """Handle incoming normalised event."""\n'
            f'        await self.reason(str(event), kg_context={{"event": event}})\n'
        )

        (prompts_path / "v1.md").write_text(
            f"# {cls} System Prompt v1\n\n"
            f"{description}\n\n"
            f"## Role\n\n"
            f"You are a specialist security agent within the UniShield platform.\n\n"
            f"## Constraints\n\n"
            f"- All outputs must be structured and validated\n"
            f"- Never execute write actions without HITL approval\n"
            f"- Include reasoning_summary, evidence_references, and confidence_breakdown\n"
        )


if __name__ == "__main__":
    main()
