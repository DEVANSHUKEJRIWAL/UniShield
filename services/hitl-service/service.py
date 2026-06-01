"""HITL service — human-in-the-loop decision queue."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import HITLDecisionRecord
from packages.core.redis_client import publish_audit, read_stream
from packages.shared_types.constants import RedisStream
from services.hitl_service.models import HITLDecision, HITLRequest, should_require_hitl


class HITLService:
    """Manage HITL queue and decisions."""

    SLA_MINUTES = {"P0": 5, "P1": 15, "P2": 120, "P3": 1440}

    async def get_queue(self, tenant_id: str, db: AsyncSession) -> list[dict[str, Any]]:
        """Return pending HITL items from Redis stream."""
        try:
            entries = await read_stream(RedisStream.HITL_QUEUE, count=50, block_ms=100)
            return [data for _, data in entries if data.get("tenant_id") == tenant_id]
        except Exception:
            return []

    async def decide(
        self,
        action_id: str,
        decision: HITLDecision,
        analyst_id: str,
        tenant_id: str,
        db: AsyncSession,
        modification: str | None = None,
        reasoning: str | None = None,
        original: dict[str, Any] | None = None,
    ) -> HITLDecisionRecord:
        """Record analyst decision — append-only audit."""
        record = HITLDecisionRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            agent_id=(original or {}).get("agent_id", "unknown"),
            action=original or {},
            original_recommendation=str(original),
            analyst_id=analyst_id,
            decision=decision.value,
            modification=modification,
            reasoning=reasoning,
            confidence=float((original or {}).get("confidence", 0.0)),
        )
        db.add(record)
        await publish_audit(
            {
                "action": "hitl_decision",
                "decision_id": str(record.id),
                "tenant_id": tenant_id,
                "analyst_id": analyst_id,
                "decision": decision.value,
            }
        )
        return record

    def evaluate(self, confidence: float, risk: str, severity: str) -> bool:
        """Return whether HITL is required."""
        return should_require_hitl(confidence, risk, severity)


hitl_service = HITLService()
