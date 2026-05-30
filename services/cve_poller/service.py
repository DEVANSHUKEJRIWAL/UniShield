"""NVD CVE polling service (Week 3)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from packages.core.config import settings
from packages.core.persistence import upsert_cve_records


class CVEPoller:
    """Poll NVD API and store normalised CVE records."""

    NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    async def fetch_recent(self, hours: int = 6, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch CVEs published in the last N hours."""
        start = (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000")
        headers = {}
        if settings.nvd_api_key:
            headers["apiKey"] = settings.nvd_api_key
        params: dict[str, Any] = {
            "pubStartDate": start,
            "resultsPerPage": min(limit, 100),
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(self.NVD_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    return self._mock_cves(limit)
                data = resp.json()
                return [self._normalise(item) for item in data.get("vulnerabilities", [])[:limit]]
        except Exception:
            return self._mock_cves(limit)

    async def poll_and_store(self, hours: int = 6) -> dict[str, Any]:
        """Fetch and persist CVEs."""
        cves = await self.fetch_recent(hours=hours)
        stored = await upsert_cve_records(cves)
        return {"fetched": len(cves), "stored": stored, "polled_at": datetime.now(UTC).isoformat()}

    def _normalise(self, item: dict[str, Any]) -> dict[str, Any]:
        cve = item.get("cve", {})
        cve_id = cve.get("id", "CVE-UNKNOWN")
        desc = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")
                break
        metrics = cve.get("metrics", {})
        cvss = 0.0
        severity = "medium"
        for key in ("cvssMetricV31", "cvssMetricV30"):
            if metrics.get(key):
                cvss = float(metrics[key][0]["cvssData"].get("baseScore", 0))
                severity = metrics[key][0]["cvssData"].get("baseSeverity", "medium").lower()
                break
        return {
            "cve_id": cve_id,
            "cvss_score": cvss,
            "severity": severity,
            "description": desc,
            "published": cve.get("published", "")[:10],
        }

    def _mock_cves(self, limit: int) -> list[dict[str, Any]]:
        return [
            {
                "cve_id": f"CVE-2024-{1000 + i}",
                "cvss_score": 7.5 - i * 0.3,
                "severity": "high" if i < 2 else "medium",
                "description": f"Mock CVE record {i} for local dev",
                "published": datetime.now(UTC).strftime("%Y-%m-%d"),
                "mock": True,
            }
            for i in range(min(limit, 5))
        ]


cve_poller = CVEPoller()
