"""gitlab connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class GitlabConnector(BaseConnector):
    """Integration adapter for gitlab."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from gitlab."""
        return [
            {
                "source_vendor": "gitlab",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from gitlab",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "gitlab", "action": action}
