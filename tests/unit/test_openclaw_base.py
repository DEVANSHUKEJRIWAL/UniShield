"""Unit tests for OpenClaw base agent."""

import pytest

from agents._openclaw.base import OpenClawAgent
from agents.dark_web_agent.agent import DarkWebAgent


class TestOpenClawAgent:
    """Tests for OpenClawAgent base class."""

    def test_dark_web_agent_instantiation(self) -> None:
        """Dark web agent extends OpenClawAgent."""
        agent = DarkWebAgent(
            agent_id="test-001",
            tenant_id="meridian-financial",
        )
        assert isinstance(agent, OpenClawAgent)
        assert agent.agent_name == "dark-web-agent"
        assert agent.tenant_id == "meridian-financial"

    def test_system_prompt_includes_tenant(self) -> None:
        """System prompt includes tenant context."""
        agent = DarkWebAgent(agent_id="test-001", tenant_id="meridian-financial")
        prompt = agent.get_system_prompt({"clients": []})
        assert "meridian-financial" in prompt

    @pytest.mark.asyncio
    async def test_get_tools_returns_list(self) -> None:
        """Agent tools return a list."""
        agent = DarkWebAgent(agent_id="test-001", tenant_id="meridian-financial")
        tools = await agent.get_tools()
        assert isinstance(tools, list)
