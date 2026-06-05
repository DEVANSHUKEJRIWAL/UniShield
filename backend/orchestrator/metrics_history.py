"""Historical metrics for dashboard sparklines."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.infrastructure.postgres_client import to_pg_timestamp


class MetricsHistoryStore:
    """Records and queries time-series KPI points per client."""

    def __init__(self, postgres) -> None:
        self._postgres = postgres

    async def record_snapshot(
        self,
        client_id: str,
        *,
        risk_score: int = 0,
        critical_count: int = 0,
        findings_count: int = 0,
        hitl_queue_depth: int = 0,
        active_agents: int = 0,
        compliance_gaps: int = 0,
        workflow_id: str | None = None,
    ) -> None:
        await self._postgres.execute(
            """
            INSERT INTO metrics_history
                (client_id, recorded_at, risk_score, critical_count, findings_count,
                 hitl_queue_depth, active_agents, compliance_gaps, workflow_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            client_id,
            to_pg_timestamp(datetime.now(UTC)),
            risk_score,
            critical_count,
            findings_count,
            hitl_queue_depth,
            active_agents,
            compliance_gaps,
            workflow_id,
        )

    async def sparkline_series(
        self,
        client_id: str,
        *,
        hours: int = 168,
        slots: int = 6,
    ) -> dict[str, list[int]]:
        since = datetime.now(UTC) - timedelta(hours=hours)
        rows = await self._postgres.fetch(
            """
            SELECT risk_score, critical_count, findings_count, hitl_queue_depth,
                   active_agents, compliance_gaps, recorded_at
            FROM metrics_history
            WHERE client_id = $1 AND recorded_at >= $2
            ORDER BY recorded_at ASC
            LIMIT 500
            """,
            client_id,
            to_pg_timestamp(since),
        )
        if not rows:
            return {}

        def _series(key: str) -> list[int]:
            values = [int(r.get(key) or 0) for r in rows]
            if len(values) >= slots:
                return values[-slots:]
            pad = [values[0] if values else 0] * (slots - len(values))
            return pad + values

        return {
            "risk": _series("risk_score"),
            "critical": _series("critical_count"),
            "findings": _series("findings_count"),
            "hitl": _series("hitl_queue_depth"),
            "agents": _series("active_agents"),
            "compliance": _series("compliance_gaps"),
        }
