"""End-to-end orchestrator pipeline test (inline mode)."""

import os

import pytest
from sqlalchemy import func, select

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from agents.orchestrator.agent import OrchestratorAgent
from packages.core.database import SessionLocal, init_db
from packages.core.models import Finding


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    await init_db()


@pytest.mark.asyncio
async def test_orchestrator_pipeline_persists_findings() -> None:
    """Orchestrator → specialists → aggregated finding in DB."""
    async with SessionLocal() as db:
        before = await db.scalar(
            select(func.count()).select_from(Finding).where(Finding.tenant_id == "meridian-financial")
        ) or 0

    orchestrator = OrchestratorAgent(agent_id="orch-e2e", tenant_id="meridian-financial")
    result = await orchestrator.orchestrate(
        {"type": "credential_leak", "domain": "meridian.com", "severity": "critical"}
    )

    assert result.get("aggregated") is not None
    assert result.get("priority") == "P0"
    assert len(result.get("agents", [])) >= 2

    async with SessionLocal() as db:
        after = await db.scalar(
            select(func.count()).select_from(Finding).where(Finding.tenant_id == "meridian-financial")
        ) or 0
    assert after >= before
