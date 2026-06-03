"""Workflow trigger and event schemas."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TriggerSource(str, Enum):
    """Sources that can initiate a workflow."""

    MANUAL_FRONTEND = "manual_frontend"
    SCHEDULED = "scheduled"
    CICD = "cicd"
    INCIDENT = "incident"
    ALERT_ESCALATION = "alert_escalation"
    THREAT_ACTOR = "threat_actor"


class AgentStatus(str, Enum):
    """Per-agent execution status within a workflow."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class WorkflowStatus(str, Enum):
    """Overall workflow status."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class WorkflowTrigger:
    """Internal trigger object used by the orchestrator."""

    workflow_name: str
    client_id: str
    source: TriggerSource
    incident_id: Optional[str] = None
    repo_url: Optional[str] = None
    repo_ref: Optional[str] = None
    correlation_id: Optional[str] = None
    context: dict = field(default_factory=dict)


@dataclass
class AgentCompleteEvent:
    """Kafka event emitted when an agent completes its work."""

    workflow_id: str
    agent_id: str
    client_id: str
    correlation_id: str
    status: str  # SUCCESS / FAILED
    completed_at: datetime


class WorkflowTriggerRequest(BaseModel):
    """API request body for POST /workflows/trigger."""

    workflow_id: str
    client_id: str
    repo_url: Optional[str] = None
    repo_ref: Optional[str] = None
    connection_id: Optional[str] = None
    connection_ids: list[str] = Field(default_factory=list)
    scan_all_repos: bool = False
    ref_override: Optional[str] = None
    incident_id: Optional[str] = None
    source: TriggerSource = TriggerSource.MANUAL_FRONTEND


class WorkflowApproveRequest(BaseModel):
    """API request body for POST /workflows/{id}/approve."""

    approved_by: str


class WorkflowStateResponse(BaseModel):
    """API response for workflow state queries."""

    workflow_id: str
    client_id: str
    incident_id: Optional[str] = None
    workflow_name: str
    flow_type: str
    triggered_by: str
    started_at: datetime
    agent_states: dict[str, str]
    current_step_index: int
    retry_counts: dict[str, int] = Field(default_factory=dict)
    max_retries: int = 3
    paused: bool = False
    pause_reason: Optional[str] = None
    pause_expires: Optional[datetime] = None
    approved_by: Optional[str] = None
    escalated_to_dynamic: bool = False
    completed_at: Optional[datetime] = None
    status: str
    error: Optional[str] = None
