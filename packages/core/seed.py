"""Idempotent database seed for local development."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import hash_password, verify_password
from packages.core.models import (
    AgentState,
    Client,
    Finding,
    User,
)
from packages.shared_types.constants import AgentName, UserRole

CLIENTS = [
    ("meridian-financial", "Meridian Financial Group", "BFSI"),
]

USERS = [
    ("admin@unishield.io", "admin123", UserRole.PLATFORM_ADMIN, "meridian-financial"),
    ("ciso@meridian.com", "ciso123", UserRole.CISO, "meridian-financial"),
    ("analyst@meridian.com", "analyst123", UserRole.SOC_ANALYST, "meridian-financial"),
    ("board@meridian.com", "board123", UserRole.READONLY_BOARD, "meridian-financial"),
    ("devsecops@meridian.com", "devsec123", UserRole.DEVSECOPS, "meridian-financial"),
    ("grc@meridian.com", "grc123", UserRole.GRC, "meridian-financial"),
]


async def ensure_demo_users(db: AsyncSession) -> int:
    """Upsert demo users and refresh password hashes. Returns count updated/created."""
    updated = 0
    for email, pwd, role, tenant in USERS:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        new_hash = hash_password(pwd)
        if user is None:
            db.add(User(email=email, password_hash=new_hash, role=role, tenant_id=tenant))
            updated += 1
        elif not verify_password(pwd, user.password_hash):
            user.password_hash = new_hash
            user.role = role
            user.tenant_id = tenant
            updated += 1
    if updated:
        await db.commit()
    return updated


async def seed_if_empty(db: AsyncSession) -> bool:
    """Seed demo data when no users exist. Returns True if full seed ran."""
    count = await db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        await ensure_demo_users(db)
        return False

    for cid, name, industry in CLIENTS:
        db.add(Client(id=cid, name=name, industry=industry))
    for email, pwd, role, tenant in USERS:
        db.add(
            User(
                email=email,
                password_hash=hash_password(pwd),
                role=role,
                tenant_id=tenant,
            )
        )
    for agent in AgentName:
        db.add(
            AgentState(
                agent_name=agent.value,
                tenant_id="meridian-financial",
                status="idle",
                health="healthy",
            )
        )
    findings = [
        ("Hardcoded API key in payment service", "critical", "source-code-agent", 0.95),
        ("SQL injection in user lookup endpoint", "high", "source-code-agent", 0.88),
        ("Outdated dependency with known CVE", "medium", "source-code-agent", 0.75),
    ]
    for title, sev, agent, conf in findings:
        fid = uuid.uuid4()
        db.add(
            Finding(
                id=fid,
                tenant_id="meridian-financial",
                agent_id=agent,
                type="security",
                severity=sev,
                confidence=conf,
                title=title,
                description=title,
                reasoning_summary=f"Sample SCR finding for local dashboard preview",
                mitre_ttps=["T1552"],
            )
        )
    await db.commit()
    return True
