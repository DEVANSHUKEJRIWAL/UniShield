"""Agent dispatch, retry, and aggregation (Week 2)."""

import asyncio
import uuid
from typing import Any, Literal

from packages.core.agent_messages import AgentResultMessage, AgentTaskMessage, AggregatedFinding
from packages.core.redis_client import publish_finding, publish_stream, read_stream
from packages.shared_types.constants import AgentName, RedisStream

MAX_RETRIES = 3
BACKOFF_SECONDS = (2, 4, 8)


def _create_agent(agent_name: str, tenant_id: str):
    """Lazy import to avoid circular dependency with orchestrator."""
    from agents.registry import create_agent

    return create_agent(agent_name, tenant_id)


async def publish_agent_task(message: AgentTaskMessage, agent_name: str) -> str:
    """Enqueue task on P0–P3 priority queue and specialist Redis stream."""
    payload = message.model_dump(mode="json")
    payload["agent_name"] = agent_name
    priority = str(message.priority or "P2").lower()
    if priority.startswith("p") and len(priority) == 2:
        await publish_stream(
            RedisStream.priority_queue(priority),
            {**payload, "target_agent": agent_name},
        )
    return await publish_stream(RedisStream.agent_tasks(agent_name), payload)


async def run_agent_with_retry(
    agent_name: str,
    message: AgentTaskMessage,
) -> AgentResultMessage:
    """Execute agent inline with exponential backoff retry."""
    last_error: str | None = None
    for attempt in range(MAX_RETRIES):
        try:
            from packages.core.persistence import log_agent_run

            agent = _create_agent(agent_name, message.tenant_id)
            await log_agent_run(agent_name, message.tenant_id, task_id=message.task_id, status="started", input_data=message.input)
            await agent.on_event(message.model_dump(mode="json"))
            finding = await _latest_finding(agent_name, message.tenant_id)
            return AgentResultMessage(
                task_id=message.task_id,
                agent_name=agent_name,
                tenant_id=message.tenant_id,
                status="completed",
                finding=finding,
                retries=attempt,
            )
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(BACKOFF_SECONDS[attempt])
    return AgentResultMessage(
        task_id=message.task_id,
        agent_name=agent_name,
        tenant_id=message.tenant_id,
        status="error",
        error=last_error,
        retries=MAX_RETRIES,
    )


async def _latest_finding(agent_name: str, tenant_id: str) -> dict[str, Any] | None:
    """Read most recent finding from agent findings stream."""
    stream = RedisStream.agent_findings(agent_name)
    entries = await read_stream(stream, last_id="0", count=20, block_ms=100)
    for _msg_id, data in reversed(entries):
        if data.get("tenant_id") == tenant_id:
            return data
    return None


async def dispatch_agents(
    event: dict[str, Any],
    tenant_id: str,
    agent_names: list[str],
    priority: str,
    *,
    mode: Literal["inline", "queue"] = "inline",
    parent_event_id: str | None = None,
) -> list[AgentResultMessage]:
    """Dispatch event to multiple agents (parallel for P0/P1)."""
    from agents.orchestrator.routing import should_run_parallel

    parallel = should_run_parallel(priority)
    context: dict[str, Any] = {"event": event, "prior_findings": []}
    results: list[AgentResultMessage] = []

    async def _one(name: str) -> AgentResultMessage:
        msg = AgentTaskMessage(
            parent_event_id=parent_event_id or event.get("event_id"),
            tenant_id=tenant_id,
            priority=priority,
            input={**event, "payload": event.get("payload", event)},
            context=context,
            triggered_by="orchestrator",
        )
        if mode == "queue":
            await publish_agent_task(msg, name)
            return AgentResultMessage(
                task_id=msg.task_id,
                agent_name=name,
                tenant_id=tenant_id,
                status="queued",
            )
        return await run_agent_with_retry(name, msg)

    if parallel:
        outcomes = await asyncio.gather(*[_one(n) for n in agent_names], return_exceptions=True)
        for name, outcome in zip(agent_names, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                results.append(
                    AgentResultMessage(
                        task_id=str(uuid.uuid4()),
                        agent_name=name,
                        tenant_id=tenant_id,
                        status="error",
                        error=str(outcome),
                    )
                )
            else:
                results.append(outcome)
    else:
        for name in agent_names:
            result = await _one(name)
            results.append(result)
            if result.finding:
                context["prior_findings"].append(result.finding)

    return results


def aggregate_results(
    tenant_id: str,
    event: dict[str, Any],
    results: list[AgentResultMessage],
) -> AggregatedFinding:
    """Merge specialist results into a single aggregated finding."""
    completed = [r for r in results if r.status == "completed"]
    findings = [r.finding for r in completed if r.finding]
    agents = [r.agent_name for r in completed]

    severities = [f.get("severity", "medium") for f in findings if f]
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    top_severity = max(severities, key=lambda s: severity_rank.get(s, 0), default="medium")

    confidences = [float(f.get("confidence", 0.75)) for f in findings if f]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    titles = [f.get("title", "") for f in findings if f and f.get("title")]
    description = "; ".join(titles[:3]) if titles else f"Analysis for {event.get('type', 'event')}"

    return AggregatedFinding(
        tenant_id=tenant_id,
        severity=top_severity,
        confidence=round(avg_confidence, 2),
        title=f"Orchestrated: {event.get('type', 'security event')}",
        description=description,
        contributing_agents=agents,
        findings=[f for f in findings if f],
        recommended_actions=_dedupe_actions(findings),
    )


async def publish_aggregated_finding(aggregated: AggregatedFinding) -> str:
    """Publish aggregated finding to orchestrator findings stream and DB."""
    data = aggregated.model_dump(mode="json")
    msg_id = await publish_finding(AgentName.ORCHESTRATOR, data)
    try:
        from packages.core.persistence import persist_finding

        await persist_finding(
            {
                **data,
                "finding_id": data.get("finding_id"),
                "agent_id": AgentName.ORCHESTRATOR,
                "type": "aggregated",
                "title": data.get("title", "Aggregated finding"),
                "description": data.get("description", ""),
                "reasoning_summary": f"Aggregated from {', '.join(data.get('contributing_agents', []))}",
            }
        )
    except Exception:
        pass
    return msg_id


def _dedupe_actions(findings: list[dict[str, Any] | None]) -> list[str]:
    seen: set[str] = set()
    actions: list[str] = []
    for f in findings:
        if not f:
            continue
        for action in f.get("recommended_actions", []):
            if action not in seen:
                seen.add(action)
                actions.append(action)
    return actions
