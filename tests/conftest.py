"""Pytest configuration — enable OpenClaw test mocks for the suite."""

from __future__ import annotations

import pytest

from backend.agents.openclaw_setup import configure_openclaw_agents


@pytest.fixture(scope="session", autouse=True)
def _openclaw_test_mocks():
    configure_openclaw_agents(mock_mode=True)
