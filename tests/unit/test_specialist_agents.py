"""Specialist agent structured handler tests (Week 3–4)."""

import os
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from agents.insider_threat_agent.agent import InsiderThreatAgent
from agents.siem_analysis_agent.agent import SiemAnalysisAgent
from agents.threat_intel_agent.agent import ThreatIntelAgent
from agents.vulnerability_agent.agent import VulnerabilityAgent
from packages.core.database import init_db


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    await init_db()


@pytest.mark.asyncio
async def test_insider_anomalous_login_mock_finding() -> None:
    agent = InsiderThreatAgent(agent_id="t1", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event({"type": "anomalous_login", "user_id": "alice", "tenant_id": "meridian-financial"})
    emit.assert_called_once()


@pytest.mark.asyncio
async def test_threat_intel_ioc_mock_finding() -> None:
    agent = ThreatIntelAgent(agent_id="t2", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event({"type": "ioc_observed", "indicator": "evil.bad", "tenant_id": "meridian-financial"})
    emit.assert_called_once()


@pytest.mark.asyncio
async def test_vulnerability_cve_mock_finding() -> None:
    agent = VulnerabilityAgent(agent_id="t3", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event({"type": "cve_alert", "cve_id": "CVE-2024-1234", "tenant_id": "meridian-financial"})
    emit.assert_called_once()


@pytest.mark.asyncio
async def test_siem_alert_mock_finding() -> None:
    agent = SiemAnalysisAgent(agent_id="t4", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event({"type": "siem_alert", "source": "splunk", "tenant_id": "meridian-financial"})
    emit.assert_called_once()
