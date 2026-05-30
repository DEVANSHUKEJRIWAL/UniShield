"""Persistence layer tests (Week 3)."""

import os
import uuid

import pytest

os.environ.setdefault("UNISHIELD_USE_SQLITE", "1")

from packages.core.database import SessionLocal, init_db
from packages.core.persistence import persist_finding, summarize_findings, upsert_cve_records
from packages.core.schemas import AgentFinding


@pytest.fixture(autouse=True)
async def setup_db() -> None:
    await init_db()


@pytest.mark.asyncio
async def test_persist_finding_creates_record() -> None:
    """persist_finding writes finding and returns UUID."""
    finding = AgentFinding(
        finding_id=str(uuid.uuid4()),
        tenant_id="meridian-financial",
        agent_id="test-agent",
        type="analysis",
        severity="high",
        confidence=0.9,
        title="Test finding",
        description="Persistence test",
        reasoning_summary="Unit test persistence",
    )
    fid = await persist_finding(finding)
    assert fid is not None

    summary = await summarize_findings("meridian-financial", days=30)
    assert summary["total"] >= 1


@pytest.mark.asyncio
async def test_upsert_cve_records() -> None:
    """CVE poller storage deduplicates by cve_id."""
    cve_id = f"CVE-TEST-{uuid.uuid4().hex[:8].upper()}"
    cves = [{"cve_id": cve_id, "cvss_score": 7.5, "severity": "high", "description": "test"}]
    stored = await upsert_cve_records(cves)
    assert stored == 1
    stored_again = await upsert_cve_records(cves)
    assert stored_again == 0
