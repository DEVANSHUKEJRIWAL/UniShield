"""Write-scope action approval gate."""

from __future__ import annotations

from datetime import UTC, datetime

from unishield.infrastructure.kafka_client import KafkaProducer
from unishield.infrastructure.postgres_client import PostgresClient
from unishield.orchestrator.workflow_state import WorkflowStateStore
from unishield.schemas.action_contract import (
    ActionNotFound,
    ActionScope,
    ActionStatus,
    ProposedAction,
)


class ActionGate:
    """All write-scope actions require human approval before execution."""

    def __init__(
        self,
        postgres: PostgresClient,
        kafka: KafkaProducer,
        state_store: WorkflowStateStore,
    ) -> None:
        self.postgres = postgres
        self.kafka = kafka
        self.state_store = state_store

    async def propose(self, action: ProposedAction) -> str:
        if action.scope == ActionScope.READ_ONLY:
            raise ValueError(f"READ_ONLY actions do not need approval: {action.action_type}")

        await self.postgres.execute(
            """
            INSERT INTO proposed_actions
                (action_id, workflow_id, agent_id, action_type,
                 scope, target, description, impact, reversible,
                 rollback_steps, proposed_at, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ON CONFLICT (action_id) DO NOTHING
            """,
            action.action_id,
            action.workflow_id,
            action.agent_id,
            action.action_type,
            action.scope.value,
            action.target,
            action.description,
            action.impact,
            action.reversible,
            action.rollback_steps,
            action.proposed_at,
            ActionStatus.PENDING_APPROVAL.value,
        )

        await self.kafka.publish(
            "action.pending",
            {
                "action_id": action.action_id,
                "workflow_id": action.workflow_id,
                "action_type": action.action_type,
                "target": action.target,
                "description": action.description,
                "impact": action.impact,
                "reversible": action.reversible,
            },
            key=action.workflow_id,
        )
        return action.action_id

    async def approve(self, action_id: str, approved_by: str) -> None:
        await self.postgres.execute(
            """
            UPDATE proposed_actions
            SET status=$1, approved_by=$2, approved_at=$3
            WHERE action_id=$4
            """,
            ActionStatus.APPROVED.value,
            approved_by,
            datetime.now(UTC),
            action_id,
        )
        await self.kafka.publish(
            "action.approved",
            {"action_id": action_id, "approved_by": approved_by},
            key=action_id,
        )

    async def reject(self, action_id: str, rejected_by: str, reason: str) -> None:
        await self.postgres.execute(
            """
            UPDATE proposed_actions
            SET status=$1, rejection_reason=$2, approved_by=$3
            WHERE action_id=$4
            """,
            ActionStatus.REJECTED.value,
            reason,
            rejected_by,
            action_id,
        )

    async def is_approved(self, action_id: str) -> bool:
        row = await self.postgres.fetchrow(
            "SELECT status FROM proposed_actions WHERE action_id=$1",
            action_id,
        )
        if not row:
            raise ActionNotFound(action_id)
        return row["status"] == ActionStatus.APPROVED.value

    async def mark_executed(self, action_id: str) -> None:
        await self.postgres.execute(
            """
            UPDATE proposed_actions SET status=$1, executed_at=$2 WHERE action_id=$3
            """,
            ActionStatus.EXECUTED.value,
            datetime.now(UTC),
            action_id,
        )

    async def list_for_workflow(self, workflow_id: str) -> list[dict]:
        return await self.postgres.fetch(
            "SELECT * FROM proposed_actions WHERE workflow_id=$1 ORDER BY proposed_at",
            workflow_id,
        )
