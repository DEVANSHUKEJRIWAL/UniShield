"""Risk scoring routes."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import RiskScoreRecord
from services.api_gateway.dependencies import CurrentUser, enforce_tenant, get_current_user

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/score/{finding_id}")
async def get_risk_score(
    finding_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Risk score for a finding."""
    result = await db.execute(select(RiskScoreRecord).where(RiskScoreRecord.finding_id == finding_id))
    score = result.scalar_one_or_none()
    if not score:
        return {"finding_id": finding_id, "composite_score": 0.0, "business_risk_label": "Unknown"}
    return {
        "finding_id": finding_id,
        "composite_score": score.composite_score,
        "business_risk_label": score.business_risk_label,
        "dimensions": score.dimensions,
        "regulatory_exposure": score.regulatory_exposure,
        "recommended_actions": score.recommended_actions,
    }


@router.get("/history/{client_id}")
async def risk_history(
    client_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Risk score history for tenant."""
    enforce_tenant(user, client_id)
    result = await db.execute(
        select(RiskScoreRecord)
        .where(RiskScoreRecord.tenant_id == client_id)
        .order_by(RiskScoreRecord.created_at.desc())
        .limit(50)
    )
    return [
        {
            "finding_id": s.finding_id,
            "composite_score": s.composite_score,
            "label": s.business_risk_label,
            "created_at": s.created_at.isoformat(),
        }
        for s in result.scalars().all()
    ]
