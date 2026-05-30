"use client";

interface HITLAction {
  action_id?: string;
  agent_id?: string;
  confidence?: number;
  reasoning?: string;
  action?: Record<string, unknown>;
}

interface HITLDecisionCardProps {
  action: HITLAction;
  onDecide: (decision: "accept" | "modify" | "reject", reasoning?: string) => void;
}

export function HITLDecisionCard({ action, onDecide }: HITLDecisionCardProps) {
  return (
    <div className="obsidian-card border-l-4 border-l-[var(--warning)]">
      <div className="flex items-start justify-between">
        <div>
          <p className="mono text-xs text-[var(--warning)]">HITL DECISION REQUIRED</p>
          <p className="mt-1 font-medium">{action.agent_id ?? "Agent"} proposed action</p>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">{action.reasoning ?? "Review recommended action"}</p>
          <p className="mono mt-2 text-xs text-[var(--text-muted)]">
            Confidence: {((action.confidence ?? 0) * 100).toFixed(0)}%
          </p>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => onDecide("accept")}
          className="rounded bg-[var(--success)] px-3 py-1.5 text-xs font-medium text-white"
        >
          Accept
        </button>
        <button
          onClick={() => onDecide("modify")}
          className="rounded bg-[var(--warning)] px-3 py-1.5 text-xs font-medium text-white"
        >
          Modify
        </button>
        <button
          onClick={() => onDecide("reject")}
          className="rounded bg-[var(--danger)] px-3 py-1.5 text-xs font-medium text-white"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
