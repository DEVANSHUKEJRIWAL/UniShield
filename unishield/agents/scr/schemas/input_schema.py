"""SCR agent input schema."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TriggerSource(str, Enum):
    """What triggered the SCR scan."""

    CICD_PIPELINE = "cicd_pipeline"
    PULL_REQUEST = "pull_request"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"


class ScanMode(str, Enum):
    """Scope of the source code scan."""

    FULL_REPO = "full_repo"
    INCREMENTAL = "incremental"
    FILE_LIST = "file_list"
    SINGLE_FILE = "single_file"


class SCRAgentInput(BaseModel):
    """Input contract for the UniShield-SCR agent."""

    model_config = ConfigDict(use_enum_values=True)

    request_id: str
    client_id: str
    workflow_id: str
    triggered_by: TriggerSource
    scan_mode: ScanMode
    repo_url: Optional[str] = None
    repo_ref: Optional[str] = None
    repo_auth_token: Optional[str] = None
    file_paths: list[str] = Field(default_factory=list)
    raw_code: Optional[str] = None
    archive_path: Optional[str] = None
    diff_base: Optional[str] = None
    diff_head: Optional[str] = None
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["**/test/**", "**/vendor/**", "**/node_modules/**"]
    )
    max_file_size_kb: int = 500
    max_files: int = 5000
    check_categories: list[str] = Field(default_factory=list)
    severity_threshold: str = "LOW"
    frameworks: list[str] = Field(default_factory=list)
    enable_ai_analysis: bool = True
    enable_secrets: bool = True
    enable_sbom: bool = True
    enable_dataflow: bool = True
    active_incident_id: Optional[str] = None
    ioc_list: list[str] = Field(default_factory=list)
    threat_actor_ttps: list[str] = Field(default_factory=list)
    crown_jewels: list[str] = Field(default_factory=list)
    output_format: list[str] = Field(default_factory=lambda: ["json", "sarif"])
    notify_channels: list[str] = Field(default_factory=list)
    correlation_id: Optional[str] = None
