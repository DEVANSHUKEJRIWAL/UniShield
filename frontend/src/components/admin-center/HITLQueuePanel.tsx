"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { decideHITL, fetchHITLQueue } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export type HITLItem = {
  action_id: string;
  item_type?: string;
  workflow_id?: string;
  workflow_name?: string;
  agent_id: string;
  confidence?: number;
  reasoning?: string;
  severity?: string;
  priority?: string;
  sla_minutes?: number;
  requires_workflow_approval?: boolean;
  pause_reason?: string | null;
  action?: {
    alert_id?: string;
    finding_id?: string;
    title?: string;
    proposed_action?: string;
    file_path?: string;
    line_start?: number;
    cwe_id?: string;
  };
};

type Props = {
  onQueueChange?: (count: number) => void;
};

export function HITLQueuePanel({ onQueueChange }: Props) {
  const { token, tenantId, ready } = useAuth();
  const [items, setItems] = useState<HITLItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [modifyId, setModifyId] = useState<string | null>(null);
  const [modifyText, setModifyText] = useState("");

  const load = useCallback(() => {
    if (!token || !tenantId) return;
    fetchHITLQueue(tenantId, token)
      .then((q) => {
        const list = Array.isArray(q) ? q : [];
        setItems(list);
        onQueueChange?.(list.length);
      })
      .catch(() => {
        setItems([]);
        onQueueChange?.(0);
      });
  }, [token, tenantId, onQueueChange]);

  useEffect(() => {
    if (!ready) return;
    load();
  }, [ready, load]);

  const onDecide = async (item: HITLItem, decision: "accept" | "modify" | "reject") => {
    if (!token || !tenantId) return;
    if (decision === "modify" && modifyId !== item.action_id) {
      setModifyId(item.action_id);
      return;
    }
    setBusyId(item.action_id);
    try {
      await decideHITL(
        item.action_id,
        tenantId,
        token,
        decision,
        {
          agent_id: item.agent_id,
          workflow_id: item.workflow_id,
          alert_id: item.action?.alert_id,
          finding_id: item.action?.finding_id,
          confidence: item.confidence,
          title: item.action?.title,
        },
        decision === "modify" ? modifyText : undefined
      );
      toast.success(`Decision: ${decision}`);
      setModifyId(null);
      setModifyText("");
      load();
    } catch {
      toast.error("HITL decision failed");
    } finally {
      setBusyId(null);
    }
  };

  if (!items.length) {
    return (
      <div className="card hitl-empty-state">
        <div className="eyebrow">HITL queue</div>
        <p className="t-title" style={{ fontSize: 14, margin: "8px 0 4px" }}>
          No pending approvals
        </p>
        <p className="t-muted" style={{ fontSize: 12, margin: 0 }}>
          Critical and high-severity findings from live SCR workflows appear here when human
          approval is required. Review each item, then accept to finalize the workflow or reject to
          hold remediation.
        </p>
      </div>
    );
  }

  return (
    <div className="hitl-queue-list">
      {items.map((item) => (
        <div key={item.action_id} className="card hitl-card">
          <div className="hitl-card-head">
            <div>
              <span className="pill-hitl">HITL required</span>
              <span className="mono t-muted" style={{ fontSize: 10, marginLeft: 8 }}>
                {item.priority ?? "P1"} · SLA {item.sla_minutes ?? 15}m
              </span>
            </div>
            <span
              className="mono"
              style={{
                fontSize: 11,
                color: item.severity === "critical" ? "var(--r-sec2)" : "var(--r-sec1)",
                fontWeight: 700,
                textTransform: "uppercase",
              }}
            >
              {item.severity ?? "high"}
            </span>
          </div>

          <p className="t-title" style={{ fontSize: 14, margin: "10px 0 4px" }}>
            {item.action?.title ?? "Agent proposed action"}
          </p>
          <p className="mono t-muted" style={{ fontSize: 11, margin: "0 0 8px" }}>
            {item.agent_id}
            {item.workflow_id ? ` · ${item.workflow_id}` : ""}
            {item.action?.file_path ? ` · ${item.action.file_path}:${item.action.line_start ?? "?"}` : ""}
          </p>
          <p className="mono t-muted" style={{ fontSize: 11, margin: "0 0 8px" }}>
            Proposed: {item.action?.proposed_action ?? "review"}
          </p>
          <p className="t-muted" style={{ fontSize: 12, lineHeight: 1.45, margin: "0 0 10px" }}>
            {item.reasoning ?? "Review recommended containment action before execution."}
          </p>
          <p className="mono t-muted" style={{ fontSize: 10 }}>
            Confidence {Math.round((item.confidence ?? 0.85) * 100)}%
          </p>

          {modifyId === item.action_id ? (
            <div style={{ marginTop: 12 }}>
              <textarea
                className="ac-form-control"
                style={{ width: "100%", minHeight: 72, borderRadius: 8, resize: "vertical" }}
                placeholder="Describe modification to the proposed action…"
                value={modifyText}
                onChange={(e) => setModifyText(e.target.value)}
              />
            </div>
          ) : null}

          <div className="hitl-actions">
            <button
              type="button"
              className="btn-accent hitl-btn-accept"
              disabled={busyId === item.action_id}
              onClick={() => onDecide(item, "accept")}
            >
              {busyId === item.action_id ? "…" : "Accept"}
            </button>
            <button
              type="button"
              className="btn-ghost hitl-btn-modify"
              disabled={busyId === item.action_id}
              onClick={() => onDecide(item, "modify")}
            >
              {modifyId === item.action_id ? "Confirm modify" : "Modify"}
            </button>
            <button
              type="button"
              className="btn-ghost hitl-btn-reject"
              disabled={busyId === item.action_id}
              onClick={() => onDecide(item, "reject")}
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
