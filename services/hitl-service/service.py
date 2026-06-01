"""HITL service — human-in-the-loop decision queue."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import Alert, Finding, HITLDecisionRecord
from packages.core.redis_client import publish_audit, read_stream
from packages.shared_types.constants import RedisStream
from services.hitl_service.models import HITLDecision, should_require_hitl


class HITLService:
    """Manage HITL queue and decisions."""

    SLA_MINUTES = {"P0": 5, "P1": 15, "P2": 120, "P3": 1440}

    async def get_queue(self, tenant_id: str, db: AsyncSession) -> list[dict[str, Any]]:
        """Return pending HITL items from Redis stream, with DB fallback when Redis is empty."""
        try:
            entries = await read_stream(RedisStream.HITL_QUEUE, count=50, block_ms=100)
            redis_items = [data for _, data in entries if data.get("tenant_id") == tenant_id]
            if redis_items:
                return redis_items
        except Exception:
            pass
        return await self._queue_from_db(tenant_id, db)

    async def _queue_from_db(self, tenant_id: str, db: AsyncSession) -> list[dict[str, Any]]:
        """Build HITL queue from open critical/high alerts when Redis has no entries."""
        decided = await db.execute(
            select(HITLDecisionRecord).where(HITLDecisionRecord.tenant_id == tenant_id)
        )
        decided_alert_ids: set[str] = set()
        for record in decided.scalars().all():
            action = record.action if isinstance(record.action, dict) else {}
            if action.get("alert_id"):
                decided_alert_ids.add(str(action["alert_id"]))

        result = await db.execute(
            select(Alert, Finding)
            .join(Finding, Alert.finding_id == Finding.id, isouter=True)
            .where(
                Alert.tenant_id == tenant_id,
                Alert.status == "open",
                Alert.severity.in_(("critical", "high")),
            )
            .order_by(Alert.created_at.desc())
            .limit(12)
        )

        items: list[dict[str, Any]] = []
        for alert, finding in result.all():
            action_id = f"hitl-{alert.id}"
            if str(alert.id) in decided_alert_ids:
                continue
            confidence = float(finding.confidence if finding else 0.85)
            severity = alert.severity
            if not should_require_hitl(confidence, "HIGH" if severity == "critical" else "MEDIUM", severity):
                continue
            items.append(
                {
                    "action_id": action_id,
                    "tenant_id": tenant_id,
                    "agent_id": alert.source or (finding.agent_id if finding else "agent"),
                    "confidence": confidence,
                    "reasoning": (
                        finding.reasoning_summary
                        if finding and finding.reasoning_summary
                        else f"Agent proposes containment for: {alert.title}"
                    ),
                    "severity": severity,
                    "priority": "P1" if severity == "critical" else "P2",
                    "sla_minutes": self.SLA_MINUTES["P1" if severity == "critical" else "P2"],
                    "expires_at": (datetime.now(UTC) + timedelta(minutes=15)).isoformat(),
                    "action": {
                        "alert_id": str(alert.id),
                        "finding_id": str(finding.id) if finding else None,
                        "title": alert.title,
                        "proposed_action": "isolate_affected_accounts",
                        "agent_id": alert.source,
                    },
                    "source": "database",
                }
            )
        return items[:8]

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
        action_payload = dict(original or {})
        action_payload["action_id"] = action_id

        record = HITLDecisionRecord(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            agent_id=action_payload.get("agent_id", "unknown"),
            action=action_payload,
            original_recommendation=str(original),
            analyst_id=analyst_id,
            decision=decision.value,
            modification=modification,
            reasoning=reasoning,
            confidence=float(action_payload.get("confidence", 0.0)),
        )
        db.add(record)

        alert_id = action_payload.get("alert_id")
        if alert_id:
            alert_result = await db.execute(select(Alert).where(Alert.id == uuid.UUID(str(alert_id))))
            alert = alert_result.scalar_one_or_none()
            if alert and alert.tenant_id == tenant_id:
                if decision == HITLDecision.ACCEPT:
                    alert.status = "acknowledged"
                elif decision == HITLDecision.REJECT:
                    alert.status = "dismissed"
                else:
                    alert.status = "in_review"
                alert.updated_at = datetime.now(UTC)

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


hitl_service = HITLService()
