"""Week 2 orchestrator and dispatch tests."""

from unittest.mock import AsyncMock, patch

import pytest

from agents.orchestrator.agent import OrchestratorAgent
from packages.core.dispatch import aggregate_results
from packages.core.agent_messages import AgentResultMessage


def test_aggregate_merges_contributing_agents() -> None:
    results = [
        AgentResultMessage(
            task_id="1",
            agent_name="dark-web-agent",
            tenant_id="meridian-financial",
            status="completed",
            finding={"severity": "critical", "confidence": 0.9, "title": "Cred leak"},
        ),
        AgentResultMessage(
            task_id="2",
            agent_name="threat-intel-agent",
            tenant_id="meridian-financial",
            status="completed",
            finding={"severity": "high", "confidence": 0.8, "title": "IOC match"},
        ),
    ]
    agg = aggregate_results("meridian-financial", {"type": "credential_leak"}, results)
    assert agg.severity == "critical"
    assert set(agg.contributing_agents) == {"dark-web-agent", "threat-intel-agent"}
    assert len(agg.findings) == 2


@pytest.mark.asyncio
async def test_orchestrator_credential_leak_workflow() -> None:
    """End-to-end orchestrator invokes mapped agents and aggregates."""
    orch = OrchestratorAgent(agent_id="test-orch", tenant_id="meridian-financial")
    with patch("agents.orchestrator.agent.publish_aggregated_finding", new_callable=AsyncMock) as pub:
        with patch("agents._openclaw.base.publish_finding", new_callable=AsyncMock):
            with patch("agents._openclaw.base.publish_hitl_request", new_callable=AsyncMock):
                with patch("packages.core.dispatch.read_stream", new_callable=AsyncMock, return_value=[]):
                    result = await orch.orchestrate(
                        {"type": "credential_leak", "domain": "meridian.com", "severity": "critical"}
                    )
    assert "dark-web-agent" in result["agents"]
    assert result["aggregated"] is not None
    assert pub.called
