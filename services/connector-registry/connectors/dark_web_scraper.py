"""dark_web_scraper connector."""

from typing import Any

from services.connector_registry.connectors.base import BaseConnector


class DarkWebScraperConnector(BaseConnector):
    """Integration adapter for dark_web_scraper."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull events from dark_web_scraper."""
        return [
            {
                "source_vendor": "dark_web_scraper",
                "source_type": "connector",
                "tenant_id": self.tenant_id,
                "mock": True,
                "message": "Mock event from dark_web_scraper",
            }
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "dark_web_scraper", "action": action}
