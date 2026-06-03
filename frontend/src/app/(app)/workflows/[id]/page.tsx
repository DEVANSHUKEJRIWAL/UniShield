"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { useWorkflowDetail } from "@/hooks/useWorkflows";

export default function WorkflowDetailPage({ params }: { params: { id: string } }) {
  const { workflow, output, loading, error } = useWorkflowDetail(params.id);

  const scr = output?.snapshot?.scr as Record<string, unknown> | undefined;
  const topFindings = (scr?.top_findings as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="ac-page">
      <AdminPageHeader
        title={params.id}
        subtitle={workflow?.workflow_name ?? "Workflow detail"}
        toolbar={
          <Link href="/workflows" className="btn btn-ghost">
            <ArrowLeft style={{ width: 14, height: 14, marginRight: 6 }} />
            Back
          </Link>
        }
      />

      {loading && <p className="t-muted">Loading…</p>}
      {error && <p style={{ color: "var(--r-sec1)" }}>{error}</p>}

      {workflow && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
          <AnimatedCard className="ac-card">
            <h3 className="t-title" style={{ fontSize: 14, marginTop: 0 }}>
              Status
            </h3>
            <dl style={{ margin: 0, fontSize: 13 }}>
              <dt className="t-muted">Overall</dt>
              <dd style={{ fontWeight: 700 }}>{workflow.status}</dd>
              {workflow.error && (
                <>
                  <dt className="t-muted">Error</dt>
                  <dd style={{ color: "var(--r-sec1)" }}>{workflow.error}</dd>
                </>
              )}
              <dt className="t-muted">Started</dt>
              <dd>{new Date(workflow.started_at).toLocaleString()}</dd>
              {workflow.completed_at && (
                <>
                  <dt className="t-muted">Completed</dt>
                  <dd>{new Date(workflow.completed_at).toLocaleString()}</dd>
                </>
              )}
            </dl>
          </AnimatedCard>

          <AnimatedCard className="ac-card">
            <h3 className="t-title" style={{ fontSize: 14, marginTop: 0 }}>
              Agent progress
            </h3>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {Object.entries(workflow.agent_states).map(([agent, state]) => (
                <li
                  key={agent}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "6px 0",
                    borderBottom: "1px solid var(--border-default)",
                    fontSize: 13,
                  }}
                >
                  <span>{agent}</span>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {state}
                  </span>
                </li>
              ))}
            </ul>
          </AnimatedCard>
        </div>
      )}

      {scr && (
        <div style={{ marginBottom: 16 }}>
          <AnimatedCard className="ac-card">
          <h3 className="t-title" style={{ fontSize: 14, marginTop: 0 }}>
            SCR summary
          </h3>
          <p className="mono t-muted" style={{ fontSize: 12 }}>
            Risk {String(scr.risk_score)} · {String(scr.highest_severity)} ·{" "}
            {String(scr.secret_findings_count ?? 0)} secrets
          </p>
          {topFindings.length > 0 && (
            <ul style={{ margin: "12px 0 0", paddingLeft: 18, fontSize: 13 }}>
              {topFindings.map((f, i) => (
                <li key={String(f.finding_id ?? i)}>
                  <strong>{String(f.severity)}</strong> — {String(f.file_path)} ({String(f.category)})
                </li>
              ))}
            </ul>
          )}
          </AnimatedCard>
        </div>
      )}

      {output && (
        <AnimatedCard className="ac-card">
          <h3 className="t-title" style={{ fontSize: 14, marginTop: 0 }}>
            Full output snapshot
          </h3>
          <pre
            style={{
              margin: 0,
              fontSize: 11,
              overflow: "auto",
              maxHeight: 480,
              background: "var(--bg-base)",
              padding: 12,
              borderRadius: 8,
            }}
          >
            {JSON.stringify(output, null, 2)}
          </pre>
        </AnimatedCard>
      )}

      {workflow?.status === "COMPLETED" && !output && (
        <p className="t-muted">Workflow completed but output not yet available in Postgres.</p>
      )}
    </div>
  );
}
