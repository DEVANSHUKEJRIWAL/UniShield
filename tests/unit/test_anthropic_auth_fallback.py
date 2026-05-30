"""Anthropic reason() auth failure fallback."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import AuthenticationError

from agents.threat_intel_agent.agent import ThreatIntelAgent


@pytest.mark.asyncio
async def test_reason_falls_back_on_authentication_error() -> None:
    agent = ThreatIntelAgent(agent_id="ti-test", tenant_id="meridian-financial")
    auth_error = AuthenticationError(
        message="invalid x-api-key",
        response=MagicMock(status_code=401),
        body={"type": "error", "error": {"type": "authentication_error"}},
    )

    with patch("agents._openclaw.base.anthropic_live_enabled", return_value=True):
        with patch.object(agent.client.messages, "create", side_effect=auth_error):
            with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
                result = await agent.reason('{"type":"manual_run"}', kg_context={})

    assert "Mock analysis" in result
    emit.assert_awaited_once()
    finding = emit.await_args.args[0]
    assert "auth failed" in finding.title.lower()
    assert "rejected" in finding.reasoning_summary.lower()
