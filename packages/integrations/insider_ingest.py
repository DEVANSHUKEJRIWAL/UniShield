"""Insider threat log ingest scaffolds (Okta, Splunk, HR)."""

from __future__ import annotations

from typing import Any

import httpx

from packages.core.config import settings


async def fetch_okta_access_logs(user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Fetch Okta system log events when OKTA_DOMAIN + OKTA_API_TOKEN configured."""
    domain = settings.okta_domain.strip()
    token = settings.okta_api_token.strip()
    if not domain or not token:
        return []
    base = domain if domain.startswith("https://") else f"https://{domain}"
    url = f"{base}/api/v1/logs"
    params: dict[str, Any] = {"limit": min(limit, 100)}
    if user_id:
        params["filter"] = f'actor.id eq "{user_id}"'
    headers = {"Authorization": f"SSWS {token}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return []
            events: list[dict[str, Any]] = []
            for row in resp.json():
                actor = row.get("actor", {})
                client_info = row.get("client", {})
                geo = row.get("client", {}).get("geographicalContext", {})
                events.append(
                    {
                        "type": "login",
                        "user_id": actor.get("alternateId") or actor.get("id"),
                        "timestamp": row.get("published"),
                        "ipCountry": geo.get("country"),
                        "deviceTrust": client_info.get("device") != "Unknown",
                        "action": row.get("displayMessage"),
                        "live": True,
                    }
                )
            return events
    except Exception:
        return []


async def fetch_splunk_access_logs(query: str = "search index=* auth | head 50", limit: int = 50) -> list[dict[str, Any]]:
    """Pull normalised access events via Splunk connector."""
    from services.connector_registry.connectors.splunk import SplunkConnector

    if not settings.splunk_url or not settings.splunk_token:
        return []
    connector = SplunkConnector(
        tenant_id="meridian-financial",
        config={"url": settings.splunk_url, "token": settings.splunk_token, "query": query},
    )
    raw = await connector.ingest()
    events: list[dict[str, Any]] = []
    for row in raw[:limit]:
        if row.get("mock"):
            continue
        events.append(
            {
                "type": row.get("event_type", "access"),
                "user_id": row.get("user", "unknown"),
                "timestamp": row.get("timestamp"),
                "recordCount": row.get("bytes", 0),
                "action": row.get("message", ""),
                "live": True,
            }
        )
    return events


async def fetch_hr_flags(org: str) -> list[dict[str, Any]]:
    """Fetch HR offboarding/risk flags from configured feed URL or CSV endpoint."""
    url = settings.hr_feed_url.strip()
    if not url:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            if "json" in resp.headers.get("content-type", ""):
                data = resp.json()
                if isinstance(data, list):
                    return [{**row, "live": True} for row in data if row.get("org", org) == org or not row.get("org")]
            lines = [ln for ln in resp.text.splitlines() if ln.strip()]
            if len(lines) < 2:
                return []
            headers = [h.strip() for h in lines[0].split(",")]
            flags: list[dict[str, Any]] = []
            for line in lines[1:]:
                vals = line.split(",")
                row = dict(zip(headers, vals, strict=False))
                if row.get("org", org) == org:
                    flags.append({**row, "live": True, "hr_flag": row.get("risk_flag", "true") == "true"})
            return flags
    except Exception:
        return []
