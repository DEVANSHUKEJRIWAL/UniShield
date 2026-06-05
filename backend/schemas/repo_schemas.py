"""Repository connection schemas for VCS connectors."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VCSProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class RepoAuthMethod(str, Enum):
    PAT = "pat"
    GITHUB_APP = "github_app"
    OAUTH = "oauth"
    SSH_KEY = "ssh_key"
    DEPLOY_KEY = "deploy_key"


class RepoStatus(str, Enum):
    CONNECTED = "connected"
    AUTH_FAILED = "auth_failed"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    PENDING = "pending"


DEFAULT_EXCLUDE_PATTERNS = [
    "**/test/**",
    "**/tests/**",
    "**/vendor/**",
    "**/node_modules/**",
    "**/*.min.js",
    "**/migrations/**",
]


class RepoConnection(BaseModel):
    """Registered repo connection metadata (token stored in Vault only)."""

    model_config = ConfigDict(use_enum_values=True)

    connection_id: str
    client_id: str
    provider: VCSProvider
    auth_method: RepoAuthMethod
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str = "main"
    vault_secret_path: str
    description: Optional[str] = None
    is_crown_jewel: bool = False
    crown_jewel_paths: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDE_PATTERNS))
    include_languages: list[str] = Field(default_factory=list)
    status: RepoStatus = RepoStatus.PENDING
    last_verified_at: Optional[datetime] = None
    last_scanned_at: Optional[datetime] = None
    last_scan_id: Optional[str] = None
    error_message: Optional[str] = None
    registered_at: datetime
    registered_by: str
    updated_at: Optional[datetime] = None


class RepoConnectionCreate(BaseModel):
    """Payload for registering a new repo (token passed separately)."""

    model_config = ConfigDict(use_enum_values=True)

    client_id: str
    provider: VCSProvider
    auth_method: RepoAuthMethod = RepoAuthMethod.PAT
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str = "main"
    description: Optional[str] = None
    is_crown_jewel: bool = False
    crown_jewel_paths: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDE_PATTERNS))
    include_languages: list[str] = Field(default_factory=list)
    registered_by: str


class RepoScanTarget(BaseModel):
    """Resolved scan target for SCRAgentInput."""

    connection_id: str
    repo_url: str
    repo_ref: str
    repo_auth_token: str
    diff_base: Optional[str] = None
    diff_head: Optional[str] = None
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude_patterns: list[str] = Field(default_factory=list)
    crown_jewel_paths: list[str] = Field(default_factory=list)
    is_crown_jewel: bool = False
    scan_mode: str = "full_repo"


class MultiRepoScanRequest(BaseModel):
    client_id: str
    workflow_id: str
    connection_ids: list[str] = Field(default_factory=list)
    scan_all: bool = False
    ref_override: Optional[str] = None
    incident_id: Optional[str] = None


class RepoBulkScanStatus(BaseModel):
    bulk_scan_id: str
    client_id: str
    total_repos: int
    completed: int
    failed: int
    in_progress: int
    workflow_ids: dict[str, str]
    started_at: datetime
    completed_at: Optional[datetime] = None
