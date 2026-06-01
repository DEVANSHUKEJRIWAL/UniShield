"""Phase 2 Insider Threat scan pipeline."""

from __future__ import annotations

from typing import Any

from agents._openclaw import tools as T
from packages.core.bfsi import BFSIFinding, confidence_label, now_iso, regulators_for_industry, stable_bfsi_id
from packages.core.insider_rules import evaluate_insider_risk
from packages.integrations.insider_ingest import fetch_hr_flags, fetch_okta_access_logs, fetch_splunk_access_logs


async def run_insider_scan(
    org: str,
    industry: str = "banking",
    user_id: str | None = None,
    events: list[dict[str, Any]] | None = None,
    tenant_id: str = "meridian-financial",
) -> dict[str, Any]:
    """Insider threat scan with live ingest + rule engine."""
    regulators = regulators_for_industry(industry)
    findings: list[BFSIFinding] = []

    event_list = list(events or [])
    event_list.extend(await fetch_okta_access_logs(user_id))
    event_list.extend(await fetch_splunk_access_logs())
    if not event_list and user_id:
        event_list = [{"type": "login", "user_id": user_id, "timestamp": now_iso(), "anomalous": True}]

    hr_flags = await fetch_hr_flags(org)
    users = {user_id} if user_id else {str(e.get("user_id", "unknown")) for e in event_list}
    users.discard("unknown")

    top_risk_user = ""
    top_risk_score = 0

    for uid in users or {"unknown-user"}:
        user_events = [e for e in event_list if str(e.get("user_id", uid)) == uid] or event_list
        baseline = await T.get_user_baseline(uid, tenant_id)
        risk = evaluate_insider_risk(uid, user_events, baseline, hr_flags)
        score = int(risk["riskScore"])
        if score > top_risk_score:
            top_risk_score = score
            top_risk_user = uid

        if score < 35 and not hr_flags:
            continue

        conf = min(0.95, 0.5 + score / 200.0)
        live = any(e.get("live") for e in user_events) or any(f.get("live") for f in hr_flags)
        findings.append(
            BFSIFinding(
                id=stable_bfsi_id("ins", org, uid),
                agentId="unishield-insider",
                kind="insider-threat",
                severity=risk["severity"],
                confidence=confidence_label(conf),
                title=f"Insider risk: {uid} (score {score})",
                description=f"Triggered rules: {', '.join(risk['triggeredRules'])}",
                evidence={
                    "triggeredRules": risk["triggeredRules"],
                    "username": uid,
                    "department": baseline.get("peer_group", "unknown"),
                    "eventCount": len(user_events),
                },
                asset=uid,
                feedSource="okta/splunk/hr" if live else "rule-engine",
                remediation="Review access logs, step-up MFA, manager verification",
                regulators=regulators,
                detectedAt=now_iso(),
                dataMode="live" if live else "mock-fallback",
                riskScore=score,
            )
        )

    summary = {
        "total": len(findings),
        "topRiskUser": top_risk_user or (user_id or "none"),
        "topRiskScore": top_risk_score,
        "org": org,
        "industry": industry,
    }
    return {
        "findings": [f.model_dump() for f in findings],
        "summary": summary,
        "meta": {"tenant_id": tenant_id, "org": org},
    }
