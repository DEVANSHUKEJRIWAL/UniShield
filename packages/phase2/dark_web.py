"""Phase 2 Dark Web scan pipeline."""

from __future__ import annotations

from typing import Any

from agents._openclaw import tools as T
from packages.core.bfsi import BFSIFinding, confidence_label, now_iso, regulators_for_industry, stable_bfsi_id
from packages.integrations.crtsh import fetch_typosquat_candidates
from packages.integrations.hibp import fetch_hibp_breaches


async def run_dark_web_scan(
    domain: str,
    brand: str,
    industry: str = "banking",
    tenant_id: str = "meridian-financial",
) -> dict[str, Any]:
    """Full dark web / external intel scan returning BFSI findings."""
    domain = domain.strip().lower()
    brand = brand or domain.split(".")[0]
    regulators = regulators_for_industry(industry)
    findings: list[BFSIFinding] = []

    exposure = await T.check_credential_exposure(domain)
    data_mode = "live" if exposure.get("live") else "mock-fallback"
    if exposure.get("exposed_count", 0) > 0 or exposure.get("breach_names"):
        conf = min(0.95, 0.65 + int(exposure.get("exposed_count", 0)) * 0.0001)
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("dw-cred", domain),
                agentId="unishield-darkweb",
                kind="leaked-credential",
                severity=exposure.get("severity", "high"),
                confidence=confidence_label(conf),
                title=f"Credential exposure for {domain}",
                description=exposure.get("summary", f"Breach data for {domain}"),
                evidence={
                    "exposed_count": exposure.get("exposed_count"),
                    "breach_names": exposure.get("breach_names", []),
                    "latest_breach": exposure.get("latest_breach"),
                },
                asset=domain,
                feedSource=exposure.get("source", "hibp"),
                remediation="Force password reset, enable MFA, rotate secrets",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode=data_mode,
            )
        )

    feeds = await T.crawl_dark_web_feeds(domain, ["paste", "forum"])
    for hit in feeds[:5]:
        kind = "paste-leak" if "paste" in str(hit.get("source", "")).lower() else "brand-mention"
        if hit.get("mock"):
            kind = "paste-leak"
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("dw-feed", domain, hit.get("source", ""), hit.get("match", "")),
                agentId="unishield-darkweb",
                kind=kind,
                severity=hit.get("severity", "medium"),
                confidence="medium" if hit.get("live") else "low",
                title=f"OSINT match: {hit.get('match', domain)}",
                description=str(hit.get("snippet", ""))[:500],
                evidence=hit,
                asset=domain,
                feedSource=str(hit.get("source", "osint")),
                remediation="Review paste/forum mention and assess credential reuse",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live" if hit.get("live") else "mock-fallback",
            )
        )

    typos = await fetch_typosquat_candidates(domain, brand)
    for cand in typos.get("candidates", [])[:5]:
        lookalike = cand.get("lookalike", "")
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("dw-typo", domain, lookalike),
                agentId="unishield-darkweb",
                kind="typosquat-domain",
                severity="medium",
                confidence="high" if typos.get("live") else "low",
                title=f"Typosquat candidate: {lookalike}",
                description=f"CT log entry resembling brand {brand}",
                evidence=cand,
                asset=lookalike,
                feedSource="crt.sh",
                remediation="Monitor domain, consider takedown / defensive registration",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live" if typos.get("live") else "mock-fallback",
            )
        )

    actors = await T.search_qdrant("threat_intel", brand)
    for row in actors[:3]:
        payload = row.get("payload", row)
        text = str(payload.get("text", payload))
        if "Mock result" in text:
            continue
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("dw-actor", brand, text[:40]),
                agentId="unishield-darkweb",
                kind="threat-actor-mention",
                severity="high",
                confidence="medium",
                title=f"Threat intel corpus match for {brand}",
                description=text[:300],
                evidence={"corpus": "threat_intel", "score": row.get("score")},
                asset=brand,
                feedSource="qdrant-threat-intel",
                remediation="Correlate with SIEM and block associated IOCs",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live",
            )
        )

    summary = _summarise(findings)
    return {
        "findings": [f.model_dump() for f in findings],
        "summary": summary,
        "meta": {"tenant_id": tenant_id, "domain": domain, "brand": brand, "industry": industry},
    }


def _summarise(findings: list[BFSIFinding]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    return {
        "total": len(findings),
        "critical": by_sev["critical"],
        "high": by_sev["high"],
        "medium": by_sev["medium"],
        "low": by_sev["low"],
        "byKind": by_kind,
    }
