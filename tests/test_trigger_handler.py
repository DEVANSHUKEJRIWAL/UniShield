"""Tests for workflow trigger handler background execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.orchestrator.trigger_handler import TriggerHandler


@pytest.mark.asyncio
async def test_handle_runs_workflow_inline_when_configured():
    orchestrator = AsyncMock()
    orchestrator.start_workflow = AsyncMock(return_value="WF-inline")
    orchestrator.execute_workflow = AsyncMock()
    handler = TriggerHandler(orchestrator)

    with patch("backend.orchestrator.trigger_handler.settings") as mock_settings:
        mock_settings.inline_workflows = True
        workflow_id = await handler.handle(
            workflow_name="code-review-only",
            client_id="client-1",
            source="manual_frontend",
        )

    assert workflow_id == "WF-inline"
    orchestrator.execute_workflow.assert_awaited_once_with("WF-inline")


@pytest.mark.asyncio
async def test_background_failure_finalizes_workflow():
    orchestrator = AsyncMock()
    orchestrator.start_workflow = AsyncMock(return_value="WF-fail")
    orchestrator.execute_workflow = AsyncMock(side_effect=RuntimeError("SCR exploded"))
    orchestrator.state_store.load = AsyncMock(return_value=type("S", (), {"status": "RUNNING"})())
    orchestrator.state_store.fail = AsyncMock()
    orchestrator._finalize = AsyncMock()
    handler = TriggerHandler(orchestrator)

    with patch("backend.orchestrator.trigger_handler.settings") as mock_settings:
        mock_settings.inline_workflows = True
        await handler.handle(
            workflow_name="code-review-only",
            client_id="client-1",
            source="manual_frontend",
        )

    orchestrator.state_store.fail.assert_awaited_once()
    orchestrator._finalize.assert_awaited_once()
