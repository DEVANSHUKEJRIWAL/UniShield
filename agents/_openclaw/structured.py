"""Structured event handlers for specialist agents (Week 3–4)."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from packages.core.agent_messages import AgentTaskMessage
from packages.core.config import settings
from packages.core.schemas import AgentFinding

StructuredHandler = Callable[[Any, dict[str, Any]], Awaitable[None]]


def mock_mode() -> bool:
    """True when Anthropic key absent — use structured tool handlers."""
    return not settings.anthropic_api_key


def parse_task_event(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse Redis task or raw event into payload + kg_context."""
    try:
        task = AgentTaskMessage.from_redis(event)
        return task.input, task.kg_context()
    except ValueError:
        return event, {"event": event}


async def emit_mock_finding(
    agent: Any,
    payload: dict[str, Any],
    *,
    title: str,
    severity: str,
    confidence: float,
    description: str,
    finding_type: str = "analysis",
    recommended_actions: list[str] | None = None,
    mitre_ttps: list[str] | None = None,
    evidence: list[str] | None = None,
) -> None:
    """Emit a validated finding without LLM."""
    import uuid

    finding = AgentFinding(
        finding_id=str(uuid.uuid4()),
        tenant_id=agent.tenant_id,
        agent_id=agent.agent_name,
        type=finding_type,
        severity=severity,  # type: ignore[arg-type]
        confidence=confidence,
        title=title,
        description=description,
        reasoning_summary=f"Structured handler for event type {payload.get('type')}",
        evidence_references=evidence or [],
        mitre_ttps_matched=mitre_ttps or [],
        contributing_agents=[agent.agent_name],
        recommended_actions=recommended_actions or [],
    )
    await agent.emit_structured_finding(finding)


async def structured_on_event(
    agent: Any,
    event: dict[str, Any],
    handlers: dict[str, StructuredHandler],
    *,
    default_types: list[str] | None = None,
) -> None:
    """Route to structured handler in mock mode, else LLM reason loop."""
    payload, kg_context = parse_task_event(event)
    event_type = str(payload.get("type", ""))
    keys = [event_type, *(default_types or [])]
    if mock_mode():
        for key in keys:
            if key in handlers:
                handler = handlers[key]
                # Bound methods receive only payload; free functions receive (agent, payload)
                if getattr(handler, "__self__", None) is not None:
                    await handler(payload)
                else:
                    await handler(agent, payload)
                return
    await agent.reason(json.dumps(payload), kg_context=kg_context)
