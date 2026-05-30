"""Splunk connector — live REST search when configured, mock otherwise."""

from datetime import UTC, datetime
from typing import Any

import httpx

from packages.core.config import settings
from services.connector_registry.connectors.base import BaseConnector


class SplunkConnector(BaseConnector):
    """Integration adapter for Splunk SIEM."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull alerts/events from Splunk."""
        url = self.config.get("url") or settings.splunk_url
        token = self.config.get("token") or settings.splunk_token
        if url and token:
            return await self._live_ingest(url, token)
        return [self._mock_event()]

    async def _live_ingest(self, base_url: str, token: str) -> list[dict[str, Any]]:
        """Query Splunk search/jobs/export for recent notable events."""
        search = "| search index=notable OR index=security earliest=-1h | head 20"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"search": search, "output_mode": "json"}
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/services/search/jobs/export",
                    params=params,
                    headers=headers,
                )
                if resp.status_code != 200:
                    return [self._mock_event(live_failed=True)]
                events: list[dict[str, Any]] = []
                for line in resp.text.strip().splitlines()[:20]:
                    if not line.strip():
                        continue
                    import json

                    try:
                        row = json.loads(line)
                        result = row.get("result", row)
                        events.append(self._normalise(result))
                    except json.JSONDecodeError:
                        continue
                return events or [self._mock_event()]
        except Exception:
            return [self._mock_event(live_failed=True)]

    def _normalise(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_vendor": "splunk",
            "source_type": "siem",
            "tenant_id": self.tenant_id,
            "type": "siem_alert",
            "severity": row.get("severity", row.get("urgency", "medium")),
            "title": row.get("rule_name", row.get("search_name", "Splunk alert")),
            "src_ip": row.get("src_ip", row.get("src")),
            "user": row.get("user"),
            "timestamp": row.get("_time", datetime.now(UTC).isoformat()),
            "mock": False,
        }

    def _mock_event(self, live_failed: bool = False) -> dict[str, Any]:
        return {
            "source_vendor": "splunk",
            "source_type": "siem",
            "tenant_id": self.tenant_id,
            "type": "siem_alert",
            "severity": "high",
            "title": "Failed login burst detected",
            "src_ip": "10.0.1.45",
            "user": "admin",
            "timestamp": datetime.now(UTC).isoformat(),
            "mock": True,
            "live_failed": live_failed,
        }

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        """Execute outbound action (HITL-gated)."""
        return {"status": "queued", "connector": "splunk", "action": action}
