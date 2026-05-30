"""Week 2 agent message protocol tests."""

import pytest

from packages.core.agent_messages import AgentTaskMessage


def test_task_message_from_redis() -> None:
    msg = AgentTaskMessage.from_redis(
        {
            "task_id": "t-1",
            "tenant_id": "meridian-financial",
            "priority": "P1",
            "input": {"type": "credential_leak", "domain": "meridian.com"},
            "context": {"event_id": "e-1"},
        }
    )
    assert msg.tenant_id == "meridian-financial"
    assert msg.input["type"] == "credential_leak"
    assert msg.kg_context()["tenant_id"] == "meridian-financial"


def test_task_message_requires_tenant() -> None:
    with pytest.raises(ValueError):
        AgentTaskMessage.from_redis({"input": {}})
