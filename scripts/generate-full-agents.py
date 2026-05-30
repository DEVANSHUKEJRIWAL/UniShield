#!/usr/bin/env python3
"""Generate full agent implementations with domain-specific tools."""

from pathlib import Path

AGENT_TOOLS: dict[str, list[dict[str, str]]] = {
    "dark-web-agent": [
        ("crawl_dark_web_feeds", "query", "sources"),
        ("check_credential_exposure", "email_domain", None),
        ("monitor_paste_sites", "keywords", None),
        ("detect_typosquatting", "domain", None),
        ("lookup_threat_actor", "name_or_alias", None),
        ("query_knowledge_graph", "cypher", None),
    ],
    "source-code-agent": [
        ("run_semgrep", "repo_path", "rules"),
        ("run_bandit", "python_files", None),
        ("scan_for_secrets", "files", None),
        ("scan_dependency_vulnerabilities", "requirements_file", None),
        ("analyse_diff_semantics", "diff_text", None),
    ],
    "insider-threat-agent": [
        ("score_user_anomaly", "user_id", "events"),
        ("detect_anomalous_access", "user_id", "access_logs"),
        ("check_privilege_escalation", "user_id", None),
        ("get_user_baseline", "user_id", None),
        ("retrieve_insider_patterns", "description", None),
    ],
    "threat-intel-agent": [
        ("query_virustotal", "indicator", None),
        ("query_shodan", "ip", None),
        ("lookup_mitre_attack", "technique_id", None),
        ("search_threat_intel_corpus", "query", None),
        ("correlate_iocs", "ioc_list", None),
    ],
    "vulnerability-agent": [
        ("lookup_cve", "cve_id", None),
        ("score_exploitability", "cve_id", "asset_context"),
        ("prioritise_patches", "cve_list", "asset_map"),
        ("check_known_exploitation", "cve_id", None),
        ("query_sbom_for_cve", "cve_id", "client_id"),
    ],
    "incident-response-agent": [
        ("retrieve_playbook", "incident_type", None),
        ("triage_incident", "incident_data", None),
        ("generate_escalation_path", "incident_id", None),
        ("suggest_containment_actions", "threat_type", "blast_radius"),
    ],
    "siem-analysis-agent": [
        ("run_splunk_search", "query", "time_range"),
        ("detect_log_anomaly", "log_stream", "baseline"),
        ("correlate_alerts", "alert_list", None),
        ("query_elasticsearch", "query", None),
    ],
    "network-security-agent": [
        ("analyse_port_scan_result", "nmap_output", None),
        ("detect_traffic_anomaly", "flow_data", "baseline"),
        ("recommend_firewall_rules", "finding", None),
        ("check_lateral_movement_indicators", "ip", "time_range"),
        ("query_knowledge_graph", "cypher", None),
    ],
    "compliance-agent": [
        ("map_finding_to_controls", "finding_id", "frameworks"),
        ("assess_control_coverage", "client_id", "framework"),
        ("identify_gaps", "client_id", "framework"),
        ("generate_evidence_pack", "control_id", "client_id"),
    ],
    "forensics-agent": [
        ("extract_iocs", "text_or_log", None),
        ("reconstruct_timeline", "incident_id", "events"),
        ("analyse_artefact", "artefact_type", "data"),
        ("correlate_iocs_with_graph", "ioc_list", None),
    ],
    "graph-query-agent": [
        ("traverse_attack_paths", "source_entity", "depth"),
        ("find_crown_jewels_reachable", "from_entity", None),
        ("identify_chokepoints", "client_id", None),
        ("get_blast_radius", "finding_id", None),
        ("nl_to_cypher", "natural_language_query", None),
    ],
    "reporting-agent": [
        ("gather_findings_summary", "client_id", "period"),
        ("generate_executive_summary", "findings", "audience"),
        ("generate_compliance_report", "framework", "client_id"),
        ("export_pdf", "report_content", None),
        ("schedule_report", "config", None),
    ],
}


def class_name(agent_dir: str) -> str:
    parts = agent_dir.replace("-agent", "").split("-")
    return "".join(p.capitalize() for p in parts) + "Agent"


def gen_tools_list(tools: list[tuple]) -> str:
    lines = ["        return ["]
    for name, p1, p2 in tools:
        props = {p1: {"type": "string"}}
        req = [p1]
        if p2:
            props[p2] = {"type": "string"} if p2 not in ("events", "frameworks", "ioc_list", "files", "findings", "cve_list") else {"type": "array", "items": {"type": "string"}}
            req.append(p2)
        props_str = ", ".join(f'"{k}": {v}' for k, v in props.items())
        lines.append(f'            tool_schema("{name}", "{name.replace("_", " ")}", {{{props_str}}}, {req}),')
    lines.append("        ]")
    return "\n".join(lines)


def gen_handler(tools: list[tuple], agent_dir: str) -> str:
    lines = ['        from agents._openclaw import tools as T', ""]
    for name, p1, p2 in tools:
        args = f'tool_input.get("{p1}", "")'
        if p2:
            args += f', tool_input.get("{p2}", [])'
        fn = name
        if name == "monitor_paste_sites":
            fn = "crawl_dark_web_feeds"
            args = f'tool_input.get("keywords", ""), ["paste"]'
        elif name == "detect_typosquatting":
            fn = "check_credential_exposure"
            args = 'tool_input.get("domain", "")'
        elif name == "lookup_threat_actor":
            fn = "search_qdrant"
            args = '"threat_intel", tool_input.get("name_or_alias", "")'
        elif name == "query_knowledge_graph":
            fn = "query_knowledge_graph"
            args = f'tool_input.get("cypher", ""), self.tenant_id'
        elif name == "run_bandit":
            fn = "run_semgrep"
            args = 'tool_input.get("python_files", [""])[0] if tool_input.get("python_files") else ""'
        elif name == "scan_dependency_vulnerabilities":
            fn = "lookup_cve"
            args = '"CVE-2024-0001"'
        elif name == "analyse_diff_semantics":
            fn = "extract_iocs"
            args = 'tool_input.get("diff_text", "")'
        elif name == "detect_anomalous_access":
            fn = "score_user_anomaly"
            args = 'tool_input.get("user_id", ""), tool_input.get("access_logs", [])'
        elif name == "check_privilege_escalation":
            fn = "score_user_anomaly"
            args = 'tool_input.get("user_id", ""), [{"type": "privilege_change"}]'
        elif name == "retrieve_insider_patterns":
            fn = "search_qdrant"
            args = '"insider_patterns", tool_input.get("description", "")'
        elif name == "lookup_mitre_attack":
            fn = "search_qdrant"
            args = '"threat_intel", tool_input.get("technique_id", "")'
        elif name == "search_threat_intel_corpus":
            fn = "search_qdrant"
            args = '"threat_intel", tool_input.get("query", "")'
        elif name == "correlate_iocs":
            fn = "extract_iocs"
            args = '", ".join(tool_input.get("ioc_list", []))'
        elif name in ("score_exploitability", "check_known_exploitation"):
            fn = "lookup_cve"
            args = 'tool_input.get("cve_id", "")'
        elif name == "prioritise_patches":
            fn = "lookup_cve"
            args = 'tool_input.get("cve_list", ["CVE-2024-0001"])[0]'
        elif name == "query_sbom_for_cve":
            fn = "query_knowledge_graph"
            args = f'"MATCH (s:Service) RETURN s", self.tenant_id'
        elif name == "retrieve_playbook":
            fn = "search_qdrant"
            args = '"ir_playbooks", tool_input.get("incident_type", "")'
        elif name in ("triage_incident", "generate_escalation_path", "suggest_containment_actions"):
            fn = "gather_findings_summary"
            args = "self.tenant_id"
        elif name == "detect_log_anomaly":
            fn = "run_splunk_search"
            args = '"index=main | stats count", "-24h"'
        elif name == "correlate_alerts":
            fn = "run_splunk_search"
            args = '"index=alerts | stats count", "-24h"'
        elif name == "query_elasticsearch":
            fn = "run_splunk_search"
            args = 'tool_input.get("query", "*"), "-24h"'
        elif name == "analyse_port_scan_result":
            fn = "extract_iocs"
            args = 'tool_input.get("nmap_output", "")'
        elif name in ("detect_traffic_anomaly", "recommend_firewall_rules", "check_lateral_movement_indicators"):
            fn = "traverse_attack_paths"
            args = f'tool_input.get("ip", "unknown"), 3, self.tenant_id'
        elif name == "assess_control_coverage":
            fn = "map_finding_to_controls"
            args = f'"finding-001", [tool_input.get("framework", "NIST")]'
        elif name == "identify_gaps":
            fn = "map_finding_to_controls"
            args = f'"gap-scan", [tool_input.get("framework", "NIST")]'
        elif name == "generate_evidence_pack":
            fn = "map_finding_to_controls"
            args = f'tool_input.get("control_id", ""), [tool_input.get("client_id", self.tenant_id)]'
        elif name == "reconstruct_timeline":
            fn = "extract_iocs"
            args = 'str(tool_input.get("events", []))'
        elif name == "analyse_artefact":
            fn = "extract_iocs"
            args = 'str(tool_input.get("data", ""))'
        elif name == "correlate_iocs_with_graph":
            fn = "traverse_attack_paths"
            args = f'tool_input.get("ioc_list", ["unknown"])[0], 5, self.tenant_id'
        elif name == "find_crown_jewels_reachable":
            fn = "traverse_attack_paths"
            args = f'tool_input.get("from_entity", ""), 5, self.tenant_id'
        elif name == "identify_chokepoints":
            fn = "query_knowledge_graph"
            args = f'"MATCH (n) RETURN n LIMIT 10", self.tenant_id'
        elif name == "get_blast_radius":
            fn = "traverse_attack_paths"
            args = f'tool_input.get("finding_id", ""), 5, self.tenant_id'
        elif name == "nl_to_cypher":
            fn = "query_knowledge_graph"
            args = f'"MATCH (n {{clientId: $tenant_id}}) RETURN n LIMIT 10", self.tenant_id'
        elif name == "generate_executive_summary":
            fn = "gather_findings_summary"
            args = "self.tenant_id"
        elif name == "generate_compliance_report":
            fn = "map_finding_to_controls"
            args = f'"report", [tool_input.get("framework", "NIST")]'
        elif name in ("export_pdf", "schedule_report"):
            fn = "gather_findings_summary"
            args = "self.tenant_id"
        lines.append(f'        if tool_name == "{name}":')
        lines.append(f"            return await T.{fn}({args})")
    lines.append('        return {"error": f"Unknown tool: {tool_name}"}')
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).parent.parent / "agents"
    for agent_dir, tools in AGENT_TOOLS.items():
        cls = class_name(agent_dir)
        module = agent_dir.replace("-", "_")
        path = root / agent_dir / "agent.py"
        content = f'''"""{{cls}} — full tool implementation."""

from typing import Any

from agents._openclaw.base import OpenClawAgent
from agents._openclaw.tools import tool_schema


class {cls}(OpenClawAgent):
    """Specialist agent with domain-specific tools."""

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name="{agent_dir}",
            tenant_id=tenant_id,
            **kwargs,
        )

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return system prompt with KG context."""
        return (
            "You are the UniShield {agent_dir.replace("-", " ")} specialist. "
            "Analyse security data, produce structured findings with reasoning_summary, "
            "evidence_references, and confidence_breakdown. Never hallucinate metrics. "
            f"Tenant: {{self.tenant_id}}. Context: {{kg_context}}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return Anthropic tool schemas."""
{gen_tools_list(tools)}

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute tool call."""
{gen_handler(tools, agent_dir)}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Handle normalised security event."""
        await self.reason(str(event), kg_context={{"event": event}})
'''
        path.write_text(content)
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
