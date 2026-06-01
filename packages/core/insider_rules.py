"""Insider threat rule engine (Phase 2)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from packages.core.bfsi import severity_from_risk_score


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def evaluate_insider_risk(
    user_id: str,
    events: list[dict[str, Any]],
    baseline: dict[str, Any] | None = None,
    hr_flags: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Score insider risk 0–100 using triggered rules.
    Rules: after-hours, volume-anomaly, foreign-ip, unmanaged-device,
    privilege-escalation, post-offboarding, hr-flag.
    """
    baseline = baseline or {}
    hr_flags = hr_flags or []
    triggered: list[str] = []
    score = 0

    avg_logins = float(baseline.get("window30d", {}).get("avg_logins", 12) or 12)
    avg_volume = float(baseline.get("window30d", {}).get("avg_data_volume_mb", 450) or 450)

    for ev in events:
        ts = _parse_ts(str(ev.get("timestamp", "")))
        if ts and (ts.hour < 7 or ts.hour >= 22):
            triggered.append("after-hours")
            score += 15

        if ev.get("type") == "privilege_change" or ev.get("action") == "privilege_escalation":
            triggered.append("privilege-escalation")
            score += 25

        country = str(ev.get("ipCountry") or ev.get("country") or "")
        if country and country not in ("IN", "US", "GB", baseline.get("home_country", "IN")):
            triggered.append("foreign-ip")
            score += 20

        if ev.get("deviceTrust") is False or ev.get("device_managed") is False:
            triggered.append("unmanaged-device")
            score += 15

        records = float(ev.get("recordCount") or ev.get("data_volume_mb") or 0)
        if records and records > avg_volume * 5:
            triggered.append("volume-anomaly")
            score += 20

    if len(events) > max(avg_logins * 2, 20):
        triggered.append("volume-anomaly")
        score += 10

    for flag in hr_flags:
        if flag.get("offboarded") or flag.get("status") == "terminated":
            triggered.append("post-offboarding")
            score += 30
        if flag.get("hr_flag") or flag.get("risk_flag"):
            triggered.append("hr-flag")
            score += 20

    triggered = list(dict.fromkeys(triggered))
    score = min(100, score)
    if not triggered and events:
        triggered.append("baseline-deviation")
        score = max(score, 25)

    return {
        "user_id": user_id,
        "riskScore": score,
        "severity": severity_from_risk_score(score),
        "triggeredRules": triggered,
        "anomalous": score >= 35,
        "z_score": round(min(score / 25.0, 4.5), 2),
        "peer_group": baseline.get("peer_group", "finance-analysts"),
    }
