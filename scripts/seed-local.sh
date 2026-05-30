#!/usr/bin/env bash
# Seed local development with mock clients, users, alerts, findings, cases
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Seeding UniShield database..."

python3 << 'PYEOF'
import asyncio
import uuid
from datetime import UTC, datetime

from packages.core.auth import hash_password
from packages.core.database import init_db, SessionLocal
from packages.core.models import (
    Alert, AgentState, Case, Client, Finding, RiskScoreRecord, User,
)
from packages.shared_types.constants import AgentName, UserRole


CLIENTS = [
    ("meridian-financial", "Meridian Financial Group", "BFSI"),
    ("aerodyne-corp", "AeroDyne Corp", "Aerospace"),
    ("novatech-industries", "NovaTech Industries", "Technology"),
    ("vantage-health", "Vantage Health Systems", "Healthcare"),
    ("globaledge-logistics", "GlobalEdge Logistics", "Logistics"),
]

USERS = [
    ("admin@unishield.io", "admin123", UserRole.PLATFORM_ADMIN, "meridian-financial"),
    ("ciso@meridian.com", "ciso123", UserRole.CISO, "meridian-financial"),
    ("analyst@meridian.com", "analyst123", UserRole.SOC_ANALYST, "meridian-financial"),
    ("board@meridian.com", "board123", UserRole.READONLY_BOARD, "meridian-financial"),
    ("devsecops@meridian.com", "devsec123", UserRole.DEVSECOPS, "meridian-financial"),
    ("grc@meridian.com", "grc123", UserRole.GRC, "meridian-financial"),
]


async def seed() -> None:
    await init_db()
    async with SessionLocal() as db:
        for cid, name, industry in CLIENTS:
            db.add(Client(id=cid, name=name, industry=industry))
        for email, pwd, role, tenant in USERS:
            db.add(User(
                email=email, password_hash=hash_password(pwd),
                role=role, tenant_id=tenant,
            ))
        for agent in AgentName:
            db.add(AgentState(
                agent_name=agent.value, tenant_id="meridian-financial",
                status="idle", health="healthy",
            ))
        findings = [
            ("Credential exposure on dark web forum", "critical", "dark-web-agent", 0.92),
            ("Anomalous privileged user login pattern", "high", "insider-threat-agent", 0.87),
            ("CVE-2024-1234 affects crown-jewel service", "high", "vulnerability-agent", 0.85),
            ("Hardcoded secret in auth module", "critical", "source-code-agent", 0.95),
            ("MITRE T1078 matched in SIEM correlation", "medium", "siem-analysis-agent", 0.78),
        ]
        for title, sev, agent, conf in findings:
            fid = uuid.uuid4()
            db.add(Finding(
                id=fid, tenant_id="meridian-financial", agent_id=agent,
                type="security", severity=sev, confidence=conf,
                title=title, description=title,
                reasoning_summary=f"Automated analysis by {agent}",
                mitre_ttps=["T1078"] if "SIEM" in title else ["T1552"],
            ))
            db.add(Alert(
                tenant_id="meridian-financial", finding_id=fid,
                severity=sev, title=title, source=agent, status="open",
            ))
            db.add(RiskScoreRecord(
                finding_id=str(fid), tenant_id="meridian-financial",
                composite_score=conf * 0.9, business_risk_label=sev.capitalize(),
                dimensions={"detection_confidence": conf},
            ))
        db.add(Case(
            tenant_id="meridian-financial",
            title="Investigation: Credential Exposure — Meridian Financial",
            status="open", severity="critical",
            timeline=[
                {"ts": datetime.now(UTC).isoformat(), "event": "Dark web agent detected credential dump"},
                {"ts": datetime.now(UTC).isoformat(), "event": "HITL escalation triggered"},
            ],
            evidence=[{"agent": "dark-web-agent", "type": "breach_finding"}],
        ))
        await db.commit()
    print("Seed complete.")


asyncio.run(seed())
PYEOF

echo "==> Done. Login: analyst@meridian.com / analyst123"
