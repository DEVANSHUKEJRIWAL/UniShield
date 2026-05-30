"""Investigation and case management routes."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents._openclaw.tools import extract_iocs
from packages.core.database import get_db
from packages.core.models import Case, Finding
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, require_permission

router = APIRouter(prefix="/api/v1/investigation", tags=["investigation"])

KILL_CHAIN_STAGES = [
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Lateral Movement",
    "Exfiltration",
]


class NoteRequest(BaseModel):
    note: str
    author: str | None = None


def _kill_chain_progress(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    """Map timeline events to MITRE kill chain stages."""
    completed: list[str] = []
    for event in timeline:
        text = str(event.get("event", event.get("text", ""))).lower()
        for stage in KILL_CHAIN_STAGES:
            key = stage.split()[0].lower()
            if key in text and stage not in completed:
                completed.append(stage)
    progress = len(completed) / len(KILL_CHAIN_STAGES) if KILL_CHAIN_STAGES else 0
    return {"stages": KILL_CHAIN_STAGES, "completed": completed, "progress_pct": round(progress * 100)}


async def _case_iocs(case: Case) -> list[dict[str, Any]]:
    """Extract IOCs from case evidence and timeline text."""
    blob = " ".join(
        [str(e) for e in (case.evidence or [])]
        + [str(t.get("event", t.get("text", ""))) for t in (case.timeline or [])]
    )
    iocs = await extract_iocs(blob or "192.168.1.45 evil-c2.example.com")
    return [
        {
            "type": i.get("type", "unknown").upper(),
            "value": i.get("value", ""),
            "malicious": i.get("type") in ("ip", "domain") and "evil" in i.get("value", ""),
        }
        for i in iocs
    ]


async def _linked_findings(db: AsyncSession, tenant_id: str, case: Case) -> list[dict[str, Any]]:
    """Findings referenced in case evidence chain."""
    agent_ids = [e.get("agent") for e in (case.evidence or []) if isinstance(e, dict) and e.get("agent")]
    if not agent_ids:
        result = await db.execute(
            select(Finding).where(Finding.tenant_id == tenant_id).order_by(Finding.created_at.desc()).limit(5)
        )
    else:
        result = await db.execute(
            select(Finding).where(Finding.tenant_id == tenant_id, Finding.agent_id.in_(agent_ids)).limit(10)
        )
    return [
        {"id": str(f.id), "title": f.title, "severity": f.severity, "agent_id": f.agent_id}
        for f in result.scalars().all()
    ]


@router.get("/cases/{client_id}")
async def list_cases(
    client_id: str,
    user: CurrentUser = Depends(require_permission("read:investigation")),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List investigation cases for tenant."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(Case).where(Case.tenant_id == client_id).order_by(Case.created_at.desc()).limit(20)
    )
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "status": c.status,
            "severity": c.severity,
            "assigned_to": c.assigned_to,
            "created_at": c.created_at.isoformat(),
        }
        for c in result.scalars().all()
    ]


@router.get("/{case_id}")
async def get_case(
    case_id: uuid.UUID,
    user: CurrentUser = Depends(require_permission("read:investigation")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get investigation case with timeline, evidence chain, and IOCs."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    enforce_tenant(user, case.tenant_id)
    iocs = await _case_iocs(case)
    kill_chain = _kill_chain_progress(case.timeline or [])
    findings = await _linked_findings(db, case.tenant_id, case)
    return {
        "id": str(case.id),
        "title": case.title,
        "status": case.status,
        "severity": case.severity,
        "timeline": case.timeline,
        "evidence": case.evidence,
        "evidence_chain": findings,
        "kill_chain": kill_chain,
        "iocs": iocs,
        "assigned_to": case.assigned_to,
        "created_at": case.created_at.isoformat(),
    }


@router.post("/{case_id}/notes")
async def add_note(
    case_id: uuid.UUID,
    body: NoteRequest,
    user: CurrentUser = Depends(require_permission("write:investigation")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Add note to investigation case."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    enforce_tenant(user, case.tenant_id)
    timeline = list(case.timeline or [])
    timeline.append({"type": "note", "author": body.author or user.email, "text": body.note})
    case.timeline = timeline
    await db.commit()
    return {"status": "note_added", "case_id": str(case_id)}
