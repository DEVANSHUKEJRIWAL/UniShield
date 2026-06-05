"""Write-scope action contract."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ActionScope(str, Enum):
    READ_ONLY = "read_only"
    WRITE_SCOPE = "write_scope"


class ActionStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    ABORTED = "aborted"


@dataclass
class ProposedAction:
    """A write-scope action requiring human approval before execution."""

    action_id: str
    workflow_id: str
    agent_id: str
    action_type: str
    scope: ActionScope
    target: str
    description: str
    impact: str
    reversible: bool
    proposed_at: datetime
    rollback_steps: Optional[str] = None
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    executed_at: Optional[datetime] = None


WRITE_SCOPE_ACTIONS = {
    "isolate_host",
    "block_ip",
    "revoke_network_access",
    "push_firewall_rule",
    "revoke_credentials",
    "disable_account",
    "force_mfa_enrollment",
    "rotate_secret",
    "remediate_misconfiguration",
    "delete_s3_public_acl",
    "revoke_iam_policy",
    "apply_patch",
    "merge_fix_pr",
    "create_jira_ticket",
    "send_alert_email",
}

READ_ONLY_ACTIONS = {
    "scan_code",
    "generate_sbom",
    "read_logs",
    "fetch_threat_intel",
    "generate_report",
    "read_shared_memory",
    "write_shared_memory",
    "write_personal_memory",
}


class ActionNotFound(Exception):
    """Raised when a proposed action is not found."""

    def __init__(self, action_id: str) -> None:
        super().__init__(f"Action not found: {action_id}")
        self.action_id = action_id
