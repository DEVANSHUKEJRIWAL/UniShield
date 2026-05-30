"""Week 2 Source Code Review Agent tests."""

import pytest
from unittest.mock import AsyncMock, patch

from agents.source_code_agent.agent import SourceCodeAgent
from agents._openclaw import tools as T


@pytest.mark.asyncio
async def test_source_code_tools_list() -> None:
    agent = SourceCodeAgent(agent_id="sc-1", tenant_id="meridian-financial")
    tools = await agent.get_tools()
    names = {t["name"] for t in tools}
    assert "run_semgrep" in names
    assert "scan_for_secrets" in names
    assert "run_bandit" in names


@pytest.mark.asyncio
async def test_semgrep_mock_returns_findings() -> None:
    findings = await T.run_semgrep("/workspace")
    assert len(findings) >= 1
    assert "file" in findings[0]
    assert "rule" in findings[0]


@pytest.mark.asyncio
async def test_bandit_mock_returns_findings() -> None:
    findings = await T.run_bandit("/workspace")
    assert len(findings) >= 1


@pytest.mark.asyncio
async def test_code_commit_emits_code_finding() -> None:
    agent = SourceCodeAgent(agent_id="sc-1", tenant_id="meridian-financial")
    with patch.object(agent, "emit_structured_finding", new_callable=AsyncMock) as emit:
        await agent.on_event(
            {
                "tenant_id": "meridian-financial",
                "input": {"type": "code_commit", "repo_path": "/workspace"},
            }
        )
    emit.assert_called_once()
    finding = emit.call_args[0][0]
    assert finding.type == "code"
    assert finding.file_path
