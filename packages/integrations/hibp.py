"""Have I Been Pwned domain breach API."""

from __future__ import annotations

from typing import Any

import httpx

from packages.core.config import settings


async def fetch_hibp_breaches(domain: str, api_key: str | None = None) -> dict[str, Any]:
    """
    Query HIBP breachedaccount/domain API.
    Requires HIBP API key (hibpwnedpasswords or subscription key for domain search).
    """
    key = api_key or settings.hibp_api_key
    domain = domain.strip().lower().lstrip("@")
    if not key:
        return {"live": False, "domain": domain, "breaches": [], "exposed_count": 0}

    url = f"https://haveibeenpwned.com/api/v3/breaches?domain={domain}"
    headers = {"hibp-api-key": key, "User-Agent": "UniShield-BFSI-Platform"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return {"live": True, "domain": domain, "breaches": [], "exposed_count": 0}
            if resp.status_code != 200:
                return {
                    "live": False,
                    "domain": domain,
                    "breaches": [],
                    "exposed_count": 0,
                    "error": f"HIBP HTTP {resp.status_code}",
                }
            breaches = resp.json()
            if not isinstance(breaches, list):
                breaches = []
            latest = breaches[0].get("BreachDate") if breaches else None
            return {
                "live": True,
                "domain": domain,
                "breaches": breaches,
                "exposed_count": sum(int(b.get("PwnCount") or 0) for b in breaches),
                "latest_breach": latest,
                "breach_names": [b.get("Name") for b in breaches[:10]],
            }
    except Exception as exc:
        return {"live": False, "domain": domain, "breaches": [], "exposed_count": 0, "error": str(exc)}
