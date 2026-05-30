"""QRadar connector — demo mock pipeline with optional live REST."""

from datetime import UTC, datetime
from typing import Any

import httpx

from services.connector_registry.connectors.base import BaseConnector


class QradarConnector(BaseConnector):
    """Integration adapter for IBM QRadar."""

    async def ingest(self) -> list[dict[str, Any]]:
        """Pull offenses/events from QRadar."""
        base_url = self.config.get("QRADAR_URL", self.config.get("url", ""))
        token = self.config.get("QRADAR_TOKEN", self.config.get("token", ""))
        if base_url and token:
            return await self._live_ingest(base_url, token)
        return self._mock_pipeline()

    async def _live_ingest(self, base_url: str, token: str) -> list[dict[str, Any]]:
        headers = {"SEC": token, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/api/siem/offenses",
                    headers=headers,
                    params={"filter": "status=OPEN", "Range": "items=0-19"},
                )
                if resp.status_code != 200:
                    return self._mock_pipeline(live_failed=True)
                offenses = resp.json()
                return [self._normalise_offense(o) for o in offenses[:20]] or self._mock_pipeline()
        except Exception:
            return self._mock_pipeline(live_failed=True)

    def _normalise_offense(self, offense: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_vendor": "qradar",
            "source_type": "siem",
            "tenant_id": self.tenant_id,
            "type": "siem_alert",
            "severity": "critical" if offense.get("magnitude", 0) >= 8 else "high",
            "title": offense.get("description", f"QRadar offense {offense.get('id')}"),
            "offense_id": offense.get("id"),
            "timestamp": datetime.now(UTC).isoformat(),
            "mock": False,
        }

    def _mock_pipeline(self, live_failed: bool = False) -> list[dict[str, Any]]:
        """Demo pipeline events routed to SIEM/orchestrator agents."""
        return [
            {
                "source_vendor": "qradar",
                "source_type": "siem",
                "tenant_id": self.tenant_id,
                "type": "network_anomaly",
                "severity": "high",
                "title": "QRadar: lateral movement pattern",
                "src_ip": "10.0.2.88",
                "dst_ip": "10.0.1.10",
                "timestamp": datetime.now(UTC).isoformat(),
                "mock": True,
                "pipeline": "qradar-demo",
                "live_failed": live_failed,
            },
            {
                "source_vendor": "qradar",
                "source_type": "siem",
                "tenant_id": self.tenant_id,
                "type": "ioc_observed",
                "severity": "critical",
                "title": "QRadar: malicious domain beacon",
                "domain": "evil-c2.example.com",
                "timestamp": datetime.now(UTC).isoformat(),
                "mock": True,
                "pipeline": "qradar-demo",
            },
        ]

    async def act(self, action: dict[str, Any]) -> dict[str, Any]:
        return {"status": "queued", "connector": "qradar", "action": action}
