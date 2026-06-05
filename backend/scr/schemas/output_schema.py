"""SCR agent output schema — Pydantic v2 models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CodeFinding(BaseModel):
    """A single static analysis finding."""

    model_config = ConfigDict(extra="allow")

    finding_id: str
    scan_id: str = ""
    file_path: str
    language: str = "unknown"
    line_start: int = 0
    line_end: int = 0
    column_start: int = 0
    column_end: int = 0
    code_snippet: str = ""
    severity: str = "LOW"
    confidence: float = 0.5
    category: str = "unknown"
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
    call_chain: list[str] = Field(default_factory=list)
    data_flow: list[str] = Field(default_factory=list)
    reachable_from: list[str] = Field(default_factory=list)
    exploited_in_wild: bool = False
    cve_references: list[str] = Field(default_factory=list)
    threat_actor_relevance: list[str] = Field(default_factory=list)
    incident_relevance: bool = False
    first_introduced: Optional[str] = None
    introduced_by: Optional[str] = None
    age_days: Optional[int] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    false_positive_score: float = 0.0


class DependencyFinding(BaseModel):
    """A supply chain / dependency vulnerability finding."""

    package_name: str
    version: str
    ecosystem: str
    cve_id: str
    cvss_score: float
    severity: str
    fixed_version: Optional[str] = None
    is_transitive: bool = False
    dependency_path: list[str] = Field(default_factory=list)
    exploitable: bool = False
    exploit_available: bool = False


class SecretFinding(BaseModel):
    """A leaked secret or credential finding."""

    secret_type: str
    file_path: str
    line_number: int
    masked_value: str
    entropy_score: float
    verified_live: bool = False
    git_history_exposed: bool = False


class SCRAgentOutput(BaseModel):
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
    languages_detected: list[str] = Field(default_factory=list)
    risk_score: int
    risk_label: str
    total_findings: int
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_category: dict[str, int] = Field(default_factory=dict)
    code_findings: list[CodeFinding] = Field(default_factory=list)
    dependency_findings: list[DependencyFinding] = Field(default_factory=list)
    secret_findings: list[SecretFinding] = Field(default_factory=list)
    sbom: dict = Field(default_factory=dict)
    sbom_summary: dict = Field(default_factory=dict)
    executive_summary: str = ""
    technical_summary: str = ""
    top_risks: list[str] = Field(default_factory=list)
    remediation_plan: list[str] = Field(default_factory=list)
    compliance_gaps: list[str] = Field(default_factory=list)
    frameworks_assessed: list[str] = Field(default_factory=list)
    agent_version: str = "1.0.0"
    models_used: list[str] = Field(default_factory=list)
    tools_invoked: list[str] = Field(default_factory=list)
    correlated_findings: list[str] = Field(default_factory=list)
    forwarded_to: list[str] = Field(default_factory=list)


class AcquisitionResult(BaseModel):
    file_list: list[str] = Field(default_factory=list)


class DetectionResult(BaseModel):
    languages: dict[str, str] = Field(default_factory=dict)
    selected_rule_sets: dict[str, str] = Field(default_factory=dict)


class BatchResult(BaseModel):
    batch_id: str = ""
    code_findings: list[dict] = Field(default_factory=list)
    secret_findings: list[dict] = Field(default_factory=list)
    dep_findings: list[dict] = Field(default_factory=list)


class ThreatIntelResult(BaseModel):
    elevated_findings: list[dict] = Field(default_factory=list)
    correlated_count: int = 0


class RankingResult(BaseModel):
    ranked_findings: list[dict] = Field(default_factory=list)
