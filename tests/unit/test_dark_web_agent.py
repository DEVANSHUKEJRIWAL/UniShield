"""Week 2 Dark Web Monitoring Agent tests."""

import pytest
from unittest.mock import AsyncMock, patch

from agents.dark_web_agent.agent import DarkWebAgent
from agents._openclaw import tools as T
from packages.core.schemas import CredentialExposureAlert


@pytest.mark.asyncio
async def test_dark_web_tools_list() -> None:
    agent = DarkWebAgent(agent_id="dw-1", tenant_id="meridian-financial")
    tools = await agent.get_tools()
    names = {t["name"] for t in tools}
    assert "crawl_dark_web_feeds" in names
    assert "check_credential_exposure" in names


@pytest.mark.asyncio
async def test_credential_exposure_tool_output_shape() -> None:
    result = await T.check_credential_exposure("meridian.com")
    assert "domain" in result
    assert "exposed_count" in result
    assert "severity" in result


def test_credential_alert_schema() -> None:
    alert = CredentialExposureAlert.from_tool_result(
        {"domain": "meridian.com", "exposed_count": 47, "severity": "high", "latest_breach": "2024-11-01"}
    )
    assert alert.domain == "meridian.com"
    assert alert.severity == "high"
    assert alert.confidence > 0.5


@pytest.mark.asyncio
async def test_credential_leak_emits_breach_finding() -> None:
    agent = DarkWebAgent(agent_id="dw-1", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event(
            {
                "tenant_id": "meridian-financial",
                "input": {"type": "credential_leak", "domain": "meridian.com"},
            }
        )
    emit.assert_called_once()
    finding = emit.call_args[0][0]
    assert finding.type == "breach"
    assert finding.severity in ("critical", "high", "medium", "low")
