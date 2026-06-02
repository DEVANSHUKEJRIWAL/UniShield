"""SCR agent output schema."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CodeFinding:
    """A single static analysis finding."""

    finding_id: str
    scan_id: str
    file_path: str
    language: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    code_snippet: str
    severity: str
    confidence: float
    category: str
    cwe_id: Optional[str] = None
    cwe_name: Optional[str] = None
    owasp_category: Optional[str] = None
    mitre_technique: Optional[str] = None
    pci_control: Optional[str] = None
    ai_explanation: Optional[str] = None
    ai_attack_scenario: Optional[str] = None
    ai_business_impact: Optional[str] = None
    ai_fix: Optional[str] = None
    ai_fix_code: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    call_chain: list[str] = field(default_factory=list)
    data_flow: list[str] = field(default_factory=list)
    reachable_from: list[str] = field(default_factory=list)
    exploited_in_wild: bool = False
    cve_references: list[str] = field(default_factory=list)
    threat_actor_relevance: list[str] = field(default_factory=list)
    incident_relevance: bool = False
    first_introduced: Optional[str] = None
    introduced_by: Optional[str] = None
    age_days: Optional[int] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    false_positive_score: float = 0.0


@dataclass
class DependencyFinding:
    """A supply chain / dependency vulnerability finding."""

    package_name: str
    version: str
    ecosystem: str
    cve_id: str
    cvss_score: float
    severity: str
    fixed_version: Optional[str] = None
    is_transitive: bool = False
    dependency_path: list[str] = field(default_factory=list)
    exploitable: bool = False
    exploit_available: bool = False


@dataclass
class SecretFinding:
    """A leaked secret or credential finding."""

    secret_type: str
    file_path: str
    line_number: int
    masked_value: str
    entropy_score: float
    verified_live: bool = False
    git_history_exposed: bool = False


@dataclass
class SCRAgentOutput:
    """Complete output from a UniShield-SCR scan."""

    scan_id: str
    request_id: str
    client_id: str
    scan_mode: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    scan_status: str
    files_discovered: int
    files_scanned: int
    files_skipped: int
    lines_analyzed: int
    languages_detected: list[str]
    risk_score: int
    risk_label: str
    total_findings: int
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    code_findings: list[CodeFinding]
    dependency_findings: list[DependencyFinding]
    secret_findings: list[SecretFinding]
    sbom: dict
    sbom_summary: dict
    executive_summary: str
    technical_summary: str
    top_risks: list[str]
    remediation_plan: list[str]
    compliance_gaps: list[str]
    frameworks_assessed: list[str]
    agent_version: str
    models_used: list[str]
    tools_invoked: list[str]
    correlated_findings: list[str] = field(default_factory=list)
    forwarded_to: list[str] = field(default_factory=list)
