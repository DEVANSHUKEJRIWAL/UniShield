"""jira connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class JiraConnector(BaseConnector):
    """Integration adapter for jira."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from jira."""
        return [
            {
                "source_vendor": "jira",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from jira",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "jira", "action": action}
