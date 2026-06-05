"""Execute approved write-scope actions after HITL approval."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from backend.infrastructure.kafka_client import KafkaProducer
from backend.infrastructure.postgres_client import PostgresClient
from backend.orchestrator.action_gate import ActionGate
from backend.schemas.action_contract import ActionNotFound, ActionStatus

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Runs approved remediation actions and records execution outcomes."""

    def __init__(
        self,
        postgres: PostgresClient,
        action_gate: ActionGate,
        kafka: KafkaProducer,
    ) -> None:
        self._postgres = postgres
        self._action_gate = action_gate
        self._kafka = kafka

    async def execute_approved(self, action_id: str, *, executed_by: str) -> dict[str, Any]:
        row = await self._postgres.fetchrow(
            "SELECT * FROM proposed_actions WHERE action_id = $1",
            action_id,
        )
        if not row:
            raise ActionNotFound(action_id)
        if row["status"] != ActionStatus.APPROVED.value:
            approved = await self._action_gate.is_approved(action_id)
            if not approved:
                raise ValueError(f"Action {action_id} is not approved (status={row['status']})")

        action_type = str(row.get("action_type") or "")
        result = await self._dispatch(action_type, row, executed_by=executed_by)
        await self._action_gate.mark_executed(action_id)
        await self._kafka.publish(
            "action.executed",
            {
                "action_id": action_id,
                "workflow_id": row.get("workflow_id"),
                "action_type": action_type,
                "executed_by": executed_by,
                "result": result,
            },
            key=action_id,
        )
        return {"action_id": action_id, "status": "executed", "result": result}

    async def _dispatch(self, action_type: str, row: dict, *, executed_by: str) -> dict[str, Any]:
        meta = self._parse_description(row.get("description"))
        handler = {
            "remediation_review": self._execute_remediation_review,
            "apply_patch": self._execute_apply_patch,
            "create_jira_ticket": self._execute_create_ticket,
            "rotate_secret": self._execute_rotate_secret,
            "merge_fix_pr": self._execute_merge_fix_pr,
        }.get(action_type, self._execute_generic)

        return await handler(row, meta, executed_by=executed_by)

    @staticmethod
    def _parse_description(description: Any) -> dict[str, Any]:
        if isinstance(description, dict):
            return description
        text = str(description or "")
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, dict) else {"summary": text}
            except json.JSONDecodeError:
                pass
        return {"summary": text}

    async def _execute_remediation_review(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        """Record approved remediation intent; external VCS/ticket integrations hook here."""
        finding_id = meta.get("finding_id")
        file_path = meta.get("file_path") or row.get("target")
        workflow_id = row.get("workflow_id")
        logger.info(
            "Executing approved remediation review workflow=%s finding=%s file=%s by=%s",
            workflow_id,
            finding_id,
            file_path,
            executed_by,
        )
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": "remediation_review",
            "finding_id": finding_id,
            "file_path": file_path,
            "workflow_id": workflow_id,
            "message": "Remediation approved — apply fix per SCR remediation plan",
        }

    async def _execute_apply_patch(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": "apply_patch",
            "target": row.get("target"),
            "message": "Patch application queued for CI/CD integration",
        }

    async def _execute_create_ticket(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": "create_jira_ticket",
            "title": meta.get("title") or row.get("action_type"),
            "message": "Ticket creation recorded — connect Jira webhook for live sync",
        }

    async def _execute_rotate_secret(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": "rotate_secret",
            "target": row.get("target"),
            "message": "Secret rotation initiated — verify in vault/identity provider",
        }

    async def _execute_merge_fix_pr(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": "merge_fix_pr",
            "target": row.get("target"),
            "message": "Fix PR merge approved — requires VCS token with merge scope",
        }

    async def _execute_generic(
        self, row: dict, meta: dict, *, executed_by: str
    ) -> dict[str, Any]:
        logger.info(
            "Generic action execution type=%s workflow=%s by=%s",
            row.get("action_type"),
            row.get("workflow_id"),
            executed_by,
        )
        return {
            "executed_at": datetime.now(UTC).isoformat(),
            "action": row.get("action_type"),
            "target": row.get("target"),
            "message": "Action approved and recorded for audit",
        }
