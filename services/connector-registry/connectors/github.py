"""github connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class GithubConnector(BaseConnector):
    """Integration adapter for github."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from github."""
        return [
            {
                "source_vendor": "github",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from github",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "github", "action": action}
