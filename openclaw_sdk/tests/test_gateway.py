"""Tests for OpenClaw gateway URL helpers."""

from openclaw_sdk.gateway import map_agent_id, normalize_gateway_url


def test_normalize_gateway_url_strips_suffix():
    assert normalize_gateway_url("ws://127.0.0.1:18789/gateway") == "ws://127.0.0.1:18789/gateway"


def test_map_agent_id():
    assert map_agent_id("unishield-scr") == "scr"
    assert map_agent_id("unishield-cma") == "cma"
