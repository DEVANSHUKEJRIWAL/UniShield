"""Human-in-the-loop queue assembly for dashboard and investigation UI."""

from __future__ import annotations

import json
from typing import Any

from backend.infrastructure.postgres_client import PostgresClient
from backend.memory.shared_memory import SharedMemoryClient
from backend.orchestrator.action_gate import ActionGate
from backend.orchestrator.workflow_state import WorkflowStateStore


class HitlService:
    """Builds a unified HITL queue from paused workflows and proposed actions."""

    def __init__(
        self,
        action_gate: ActionGate,
        state_store: WorkflowStateStore,
        shared_memory: SharedMemoryClient,
        postgres: PostgresClient,
    ) -> None:
        self._action_gate = action_gate
        self._state_store = state_store
        self._shared_memory = shared_memory
        self._postgres = postgres

    async def list_queue(self, client_id: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[str] = set()

        paused = await self._state_store.list_workflows(client_id=client_id, status="PAUSED", limit=50)
        for wf in paused:
            wf_id = wf.workflow_id
            actions = await self._action_gate.list_for_workflow(wf_id)
            pending_actions = [a for a in actions if a.get("status") == "pending_approval"]
            if pending_actions:
                for action in pending_actions:
                    items.append(self._action_item(action, wf))
                    seen.add(str(action.get("action_id")))
            else:
                items.extend(await self._workflow_finding_items(wf))

        all_pending = await self._action_gate.list_pending()
        for action in all_pending:
            action_id = str(action.get("action_id"))
            if action_id in seen:
                continue
            wf_id = str(action.get("workflow_id"))
            wf = await self._state_store.load(wf_id)
            if wf and wf.client_id == client_id:
                items.append(self._action_item(action, wf))
                seen.add(action_id)

        items.sort(key=lambda x: (_severity_rank(x.get("severity", "low")), x.get("proposed_at", "")))
        return items

    async def _workflow_finding_items(self, wf) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        snapshot = None
        if await self._shared_memory.workflow_exists(wf.workflow_id):
            snapshot = await self._shared_memory.get_full_snapshot(wf.workflow_id)
        if not snapshot:
            row = await self._postgres.fetchrow(
                "SELECT snapshot FROM workflow_outputs WHERE workflow_id = $1 AND client_id = $2",
                wf.workflow_id,
                wf.client_id,
            )
            if row and row.get("snapshot"):
                snapshot = row["snapshot"]
                if isinstance(snapshot, str):
                    snapshot = json.loads(snapshot)

        scr = (snapshot or {}).get("scr") or {}
        findings = scr.get("code_findings") or scr.get("top_findings") or []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            sev = str(finding.get("severity", "medium")).lower()
            if sev not in ("critical", "high"):
                continue
            action_id = f"FINDING-{wf.workflow_id}-{finding.get('finding_id', finding.get('file_path', 'finding'))}"
            items.append(
                {
                    "action_id": action_id,
                    "item_type": "workflow_finding",
                    "workflow_id": wf.workflow_id,
                    "workflow_name": wf.workflow_name,
                    "agent_id": "unishield-scr",
                    "severity": sev,
                    "priority": "P1" if sev == "critical" else "P2",
                    "confidence": finding.get("confidence", 0.9),
                    "reasoning": finding.get("description") or finding.get("ai_rationale") or scr.get("executive_summary"),
                    "action": {
                        "title": f"{finding.get('category', 'Finding')}: {finding.get('file_path', 'unknown')}",
                        "proposed_action": "Review and approve remediation before workflow finalization",
                        "finding_id": finding.get("finding_id"),
                        "file_path": finding.get("file_path"),
                        "line_start": finding.get("line_start"),
                        "cwe_id": finding.get("cwe_id"),
                    },
                    "workflow_status": wf.status,
                    "pause_reason": wf.pause_reason,
                    "requires_workflow_approval": True,
                }
            )
        if wf.paused and not items:
            items.append(
                {
                    "action_id": f"WORKFLOW-{wf.workflow_id}",
                    "item_type": "workflow_approval",
                    "workflow_id": wf.workflow_id,
                    "workflow_name": wf.workflow_name,
                    "agent_id": "unishield-reporting",
                    "severity": "high",
                    "priority": "P1",
                    "confidence": 1.0,
                    "reasoning": wf.pause_reason or "Workflow requires human approval before finalization",
                    "action": {
                        "title": f"Approve workflow {wf.workflow_id}",
                        "proposed_action": "Finalize workflow snapshot after human review",
                    },
                    "workflow_status": wf.status,
                    "pause_reason": wf.pause_reason,
                    "requires_workflow_approval": True,
                }
            )
        return items

    @staticmethod
    def _action_item(action: dict[str, Any], wf) -> dict[str, Any]:
        meta = {}
        description = action.get("description") or ""
        if description.startswith("{"):
            try:
                meta = json.loads(description)
            except json.JSONDecodeError:
                meta = {"summary": description}
        return {
            "action_id": action.get("action_id"),
            "item_type": "proposed_action",
            "workflow_id": action.get("workflow_id"),
            "workflow_name": getattr(wf, "workflow_name", None),
            "agent_id": action.get("agent_id"),
            "severity": meta.get("severity", "high"),
            "priority": meta.get("priority", "P1"),
            "confidence": meta.get("confidence", 0.9),
            "reasoning": meta.get("reasoning") or meta.get("summary") or action.get("impact"),
            "action": {
                "title": meta.get("title") or action.get("action_type"),
                "proposed_action": action.get("action_type"),
                "finding_id": meta.get("finding_id"),
                "file_path": meta.get("file_path"),
                "line_start": meta.get("line_start"),
                "alert_id": meta.get("alert_id"),
            },
            "target": action.get("target"),
            "impact": action.get("impact"),
            "status": action.get("status"),
            "proposed_at": action.get("proposed_at"),
            "requires_workflow_approval": False,
        }


def _severity_rank(severity: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return order.get(str(severity).lower(), 4)
