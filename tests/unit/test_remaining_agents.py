"""Remaining specialist agent structured handler tests."""

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from agents.compliance_agent.agent import ComplianceAgent
from agents.forensics_agent.agent import ForensicsAgent
from agents.graph_query_agent.agent import GraphQueryAgent
from agents.incident_response_agent.agent import IncidentResponseAgent
from agents.network_security_agent.agent import NetworkSecurityAgent
from agents.reporting_agent.agent import ReportingAgent
from packages.core.database import init_db


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    await init_db()


@pytest.mark.parametrize(
    "agent_cls,event",
    [
        (ForensicsAgent, {"type": "ioc_observed", "indicator": "evil.com"}),
        (IncidentResponseAgent, {"type": "siem_alert", "tenant_id": "meridian-financial"}),
        (NetworkSecurityAgent, {"type": "network_anomaly", "ip": "10.0.0.1"}),
        (ComplianceAgent, {"type": "compliance_gap", "framework": "RBI"}),
        (GraphQueryAgent, {"type": "graph_query", "source_entity": "api-gateway"}),
        (ReportingAgent, {"type": "report_request", "report_type": "Board Summary"}),
    ],
)
@pytest.mark.asyncio
async def test_structured_handlers(agent_cls, event) -> None:
    agent = agent_cls(agent_id="t", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event({**event, "tenant_id": "meridian-financial"})
    emit.assert_called_once()
