"""Certificate transparency typosquat detection via crt.sh."""

from __future__ import annotations

from typing import Any

import httpx


async def fetch_typosquat_candidates(domain: str, brand: str | None = None) -> dict[str, Any]:
    """Find lookalike domains in CT logs."""
    domain = domain.strip().lower()
    brand = (brand or domain.split(".")[0]).lower()
    query = f"%.{brand}.%"
    url = f"https://crt.sh/?q={query}&output=json"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"live": False, "domain": domain, "candidates": [], "mock": True}
            rows = resp.json()
            if not isinstance(rows, list):
                return {"live": True, "domain": domain, "candidates": []}
            seen: set[str] = set()
            candidates: list[dict[str, Any]] = []
            for row in rows[:200]:
                name = str(row.get("name_value", "")).lower()
                for part in name.split("\n"):
                    part = part.strip().lstrip("*.")
                    if not part or part == domain or part in seen:
                        continue
                    if brand in part and part != domain:
                        seen.add(part)
                        candidates.append(
                            {
                                "lookalike": part,
                                "issuer": row.get("issuer_name"),
                                "logged_at": row.get("not_before"),
                            }
                        )
            return {"live": True, "domain": domain, "brand": brand, "candidates": candidates[:25]}
    except Exception as exc:
        return {"live": False, "domain": domain, "candidates": [], "error": str(exc), "mock": True}
