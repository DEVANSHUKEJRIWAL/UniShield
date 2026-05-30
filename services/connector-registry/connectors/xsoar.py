"""xsoar connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class XsoarConnector(BaseConnector):
    """Integration adapter for xsoar."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from xsoar."""
        return [
            {
                "source_vendor": "xsoar",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from xsoar",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "xsoar", "action": action}
