"""Agent-to-agent message protocol (Week 2)."""

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentTaskMessage(BaseModel):
    """Structured task dispatched from orchestrator to specialist agents."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_event_id: str | None = None
    tenant_id: str
    priority: str = "P2"
    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    triggered_by: str = "orchestrator"

    @classmethod
    def from_redis(cls, data: dict[str, Any]) -> "AgentTaskMessage":
        """Parse Redis stream payload into a task message."""
        if "tenant_id" not in data:
            raise ValueError("Missing tenant_id in agent task")
        return cls(
            task_id=str(data.get("task_id", uuid4())),
            parent_event_id=data.get("parent_event_id"),
            tenant_id=str(data["tenant_id"]),
            priority=str(data.get("priority", "P2")),
            input=_coerce_dict(data.get("input", {})),
            context=_coerce_dict(data.get("context", {})),
            triggered_by=str(data.get("triggered_by", "orchestrator")),
        )

    def kg_context(self) -> dict[str, Any]:
        """Build knowledge-graph context slice for agent reasoning."""
        return {
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "parent_event_id": self.parent_event_id,
            "priority": self.priority,
            **self.context,
        }


class AgentResultMessage(BaseModel):
    """Structured result returned from specialist to orchestrator."""

    task_id: str
    agent_name: str
    tenant_id: str
    status: str
    finding: dict[str, Any] | None = None
    error: str | None = None
    retries: int = 0


class AggregatedFinding(BaseModel):
    """Multi-agent aggregated output."""

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    type: str = "aggregated"
    severity: str = "medium"
    confidence: float = 0.0
    title: str = "Multi-agent analysis"
    description: str = ""
    contributing_agents: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        import json

        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"raw": value}
        except json.JSONDecodeError:
            return {"raw": value}
    return {}
