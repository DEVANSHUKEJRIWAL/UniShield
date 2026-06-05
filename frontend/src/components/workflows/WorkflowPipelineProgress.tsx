"use client";

import { AnimatedCard } from "@/components/ui/AnimatedCard";

export type ScrStageProgress = {
  id: string;
  label: string;
  status: "pending" | "running" | "done" | "failed";
  detail?: string;
};

export type WorkflowProgress = {
  workflow_id: string;
  workflow_name: string;
  status: string;
  agent_states: Record<string, string>;
  current_step_index: number;
  pipeline_steps: string[][];
  scr_progress?: {
    current_stage?: string;
    stages?: ScrStageProgress[];
    error?: string;
  } | null;
  paused?: boolean;
  pause_reason?: string | null;
};

const AGENT_LABELS: Record<string, string> = {
  scr: "Source Code Review",
  cma: "Compliance Mapping",
  reporting: "Reporting",
};

const AGENT_STATUS_COLOR: Record<string, string> = {
  PENDING: "var(--m3)",
  RUNNING: "var(--violet)",
  DONE: "var(--green)",
  FAILED: "var(--r-sec1)",
};

const STAGE_STATUS_COLOR: Record<string, string> = {
  pending: "var(--m3)",
  running: "var(--violet)",
  done: "var(--green)",
  failed: "var(--r-sec1)",
};

type Props = {
  progress: WorkflowProgress | null;
  loading?: boolean;
};

export function WorkflowPipelineProgress({ progress, loading }: Props) {
  if (loading && !progress) {
    return (
      <AnimatedCard className="ac-card" style={{ marginBottom: 16 }}>
        <p className="t-muted" style={{ margin: 0 }}>
          Loading pipeline progress…
        </p>
      </AnimatedCard>
    );
  }

  if (!progress) return null;

  const steps = progress.pipeline_steps ?? [];
  const scrStages = progress.scr_progress?.stages ?? [];

  return (
    <AnimatedCard className="ac-card" style={{ marginBottom: 16 }}>
      <h3 className="t-title" style={{ fontSize: 14, margin: "0 0 12px" }}>
        Orchestrator pipeline
      </h3>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: scrStages.length ? 16 : 0 }}>
        {steps.map((step, idx) => (
          <div key={idx} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {step.map((agentId) => {
              const key = agentId.replace("unishield-", "");
              const state = progress.agent_states[key] ?? "PENDING";
              const isCurrent = progress.current_step_index === idx && state === "RUNNING";
              return (
                <div
                  key={key}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${isCurrent ? "var(--violet)" : "var(--border-default)"}`,
                    background: isCurrent ? "rgba(139, 92, 246, 0.08)" : "var(--bg-surface)",
                    minWidth: 120,
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 700 }}>{AGENT_LABELS[key] ?? key}</div>
                  <div
                    className="mono"
                    style={{
                      fontSize: 10,
                      marginTop: 4,
                      color: AGENT_STATUS_COLOR[state] ?? "var(--m3)",
                    }}
                  >
                    {state}
                  </div>
                </div>
              );
            })}
            {idx < steps.length - 1 && (
              <span className="t-muted" style={{ fontSize: 16 }}>
                →
              </span>
            )}
          </div>
        ))}
      </div>

      {scrStages.length > 0 && (
        <>
          <p className="t-muted" style={{ fontSize: 11, margin: "0 0 8px" }}>
            SCR agent — 10 stages
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 8,
            }}
          >
            {scrStages.map((stage) => (
              <div
                key={stage.id}
                style={{
                  padding: "8px 10px",
                  borderRadius: 8,
                  border: "1px solid var(--border-default)",
                  background: stage.status === "running" ? "rgba(139, 92, 246, 0.06)" : "transparent",
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600 }}>{stage.label}</div>
                <div
                  className="mono"
                  style={{
                    fontSize: 10,
                    marginTop: 4,
                    color: STAGE_STATUS_COLOR[stage.status] ?? "var(--m3)",
                  }}
                >
                  {stage.status}
                  {stage.detail ? ` · ${stage.detail}` : ""}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {progress.scr_progress?.error && (
        <p style={{ color: "var(--r-sec1)", fontSize: 12, margin: "12px 0 0" }}>
          {progress.scr_progress.error}
        </p>
      )}
    </AnimatedCard>
  );
}
