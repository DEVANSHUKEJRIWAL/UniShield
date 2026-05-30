"""Agent registry — maps agent names to classes."""

from typing import Any, Type

from agents._openclaw.base import OpenClawAgent
from agents.compliance_agent.agent import ComplianceAgent
from agents.dark_web_agent.agent import DarkWebAgent
from agents.forensics_agent.agent import ForensicsAgent
from agents.graph_query_agent.agent import GraphQueryAgent
from agents.incident_response_agent.agent import IncidentResponseAgent
from agents.insider_threat_agent.agent import InsiderThreatAgent
from agents.network_security_agent.agent import NetworkSecurityAgent
from agents.orchestrator.agent import OrchestratorAgent
from agents.reporting_agent.agent import ReportingAgent
from agents.siem_analysis_agent.agent import SiemAnalysisAgent
from agents.source_code_agent.agent import SourceCodeAgent
from agents.threat_intel_agent.agent import ThreatIntelAgent
from agents.vulnerability_agent.agent import VulnerabilityAgent
from packages.shared_types.constants import AgentName

AGENT_CLASSES: dict[str, Type[OpenClawAgent]] = {
    AgentName.ORCHESTRATOR: OrchestratorAgent,
    AgentName.DARK_WEB: DarkWebAgent,
    AgentName.SOURCE_CODE: SourceCodeAgent,
    AgentName.INSIDER_THREAT: InsiderThreatAgent,
    AgentName.THREAT_INTEL: ThreatIntelAgent,
    AgentName.VULNERABILITY: VulnerabilityAgent,
    AgentName.INCIDENT_RESPONSE: IncidentResponseAgent,
    AgentName.SIEM_ANALYSIS: SiemAnalysisAgent,
    AgentName.NETWORK_SECURITY: NetworkSecurityAgent,
    AgentName.COMPLIANCE: ComplianceAgent,
    AgentName.FORENSICS: ForensicsAgent,
    AgentName.GRAPH_QUERY: GraphQueryAgent,
    AgentName.REPORTING: ReportingAgent,
}


def create_agent(agent_name: str, tenant_id: str, agent_id: str | None = None) -> OpenClawAgent:
    """Instantiate agent by name."""
    cls = AGENT_CLASSES.get(agent_name)
    if not cls:
        raise ValueError(f"Unknown agent: {agent_name}")
    return cls(agent_id=agent_id or f"{agent_name}-{tenant_id}", tenant_id=tenant_id)


def list_agents() -> list[dict[str, Any]]:
    """Return all registered agents."""
    return [{"name": name, "class": cls.__name__} for name, cls in AGENT_CLASSES.items()]
