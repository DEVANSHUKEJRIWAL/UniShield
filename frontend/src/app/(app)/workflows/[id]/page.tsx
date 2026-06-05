"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { ScanResultsView } from "@/components/scan/ScanResultsView";
import { WorkflowPipelineProgress } from "@/components/workflows/WorkflowPipelineProgress";
import { useAuth } from "@/lib/auth";
import { approveWorkflow } from "@/lib/workflows-api";
import { useWorkflowDetail } from "@/hooks/useWorkflows";
import { coerceList, parseScrSnapshot, type ScrSnapshot } from "@/lib/scr-parse";

export default function WorkflowDetailPage({ params }: { params: { id: string } }) {
  const { token, tenantId, email } = useAuth();
  const { workflow, output, progress, loading, error, refresh } = useWorkflowDetail(params.id);
  const [approving, setApproving] = useState(false);

  const snapshot = output?.snapshot ?? progress?.live_snapshot ?? {};
  const scr = snapshot.scr as ScrSnapshot | undefined;
  const cma = snapshot.cma as ScrSnapshot | undefined;
  const reporting = snapshot.reporting as ScrSnapshot | undefined;
  const parsed = parseScrSnapshot(scr);
  const allFindings = coerceList(scr?.code_findings).length
    ? coerceList(scr?.code_findings)
    : parsed.findings;

  const scrFailed = scr && (scr.scan_status === "FAILED" || Boolean(scr.error_message));
  const scrMissing =
    workflow?.workflow_name === "code-review-only" &&
    workflow.status === "COMPLETED" &&
    Boolean(output) &&
    !scr;
  const scrRunning =
    workflow?.workflow_name === "code-review-only" &&
    (workflow.status === "RUNNING" || workflow.agent_states?.scr === "RUNNING");
  const awaitingApproval = workflow?.status === "PAUSED" || Boolean(scr?.requires_human_approval);

  const handleApprove = async () => {
    if (!token || !tenantId || !email) return;
    setApproving(true);
    try {
      await approveWorkflow(tenantId, params.id, token, email);
      toast.success("Workflow approved — snapshot finalized");
      refresh();
    } catch (e) {
      toast.error("Approval failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="ac-page">
      <AdminPageHeader
        title={workflow?.workflow_name === "code-review-only" ? "Scan results" : params.id}
        subtitle={
          workflow?.workflow_name === "code-review-only"
            ? `Workflow ${params.id}`
            : (workflow?.workflow_name ?? "Workflow detail")
        }
        toolbar={
          <Link href="/workflows" className="btn btn-ghost">
            <ArrowLeft style={{ width: 14, height: 14, marginRight: 6 }} />
            Back
          </Link>
        }
      />

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="ac-card"
              style={{ height: 80, opacity: 0.4, animation: "pulse 1.5s infinite" }}
            />
          ))}
        </div>
      )}
      {error && <p style={{ color: "var(--r-sec1)" }}>{error}</p>}

      {progress && (workflow?.status === "RUNNING" || workflow?.status === "PAUSED") && (
        <WorkflowPipelineProgress progress={progress} />
      )}

      {awaitingApproval && workflow?.status === "PAUSED" && (
        <AnimatedCard className="ac-card" style={{ marginBottom: 16, borderColor: "var(--amber)" }}>
          <p style={{ margin: "0 0 8px", color: "var(--amber)", fontSize: 13 }}>
            This workflow is paused for human approval
            {workflow?.pause_reason ? `: ${workflow.pause_reason}` : ""}.
          </p>
          <p className="t-muted" style={{ margin: "0 0 12px", fontSize: 12 }}>
            Review each critical/high finding in the{" "}
            <Link href="/investigation?tab=hitl" style={{ color: "var(--violet)" }}>
              HITL approval queue
            </Link>
            , then finalize the workflow when ready.
          </p>
          <button type="button" className="btn btn-primary" disabled={approving} onClick={handleApprove}>
            {approving ? "Approving…" : "Approve & finalize workflow"}
          </button>
        </AnimatedCard>
      )}

      {scrRunning && !scr && (
        <p className="t-muted" style={{ marginBottom: 16 }}>
          Code review scan in progress — results will appear when SCR completes.
        </p>
      )}

      {scrMissing && (
        <AnimatedCard className="ac-card" style={{ marginBottom: 16, borderColor: "var(--r-sec1)" }}>
          <p style={{ margin: 0, color: "var(--r-sec1)", fontSize: 13 }}>
            This workflow completed without SCR output. Verify the orchestrator is running and re-scan.
          </p>
        </AnimatedCard>
      )}

      {scrFailed && (
        <AnimatedCard className="ac-card" style={{ marginBottom: 16, borderColor: "var(--amber)" }}>
          <p style={{ margin: 0, color: "var(--amber)", fontSize: 13 }}>
            SCR failed: {String(scr?.error_message ?? "unknown error")}
          </p>
        </AnimatedCard>
      )}

      {workflow && (
        <AnimatedCard className="ac-card" style={{ marginBottom: 16, padding: 16 }}>
          <dl
            style={{
              margin: 0,
              fontSize: 13,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 12,
            }}
          >
            <div>
              <dt className="t-muted">Status</dt>
              <dd style={{ fontWeight: 700, margin: 0 }}>{workflow.status}</dd>
            </div>
            <div>
              <dt className="t-muted">Started</dt>
              <dd style={{ margin: 0 }}>{new Date(workflow.started_at).toLocaleString()}</dd>
            </div>
            {workflow.completed_at && (
              <div>
                <dt className="t-muted">Completed</dt>
                <dd style={{ margin: 0 }}>{new Date(workflow.completed_at).toLocaleString()}</dd>
              </div>
            )}
            {Object.entries(workflow.agent_states).map(([agent, state]) => (
              <div key={agent}>
                <dt className="t-muted">{agent}</dt>
                <dd className="mono" style={{ fontWeight: 600, margin: 0 }}>
                  {state}
                </dd>
              </div>
            ))}
          </dl>
        </AnimatedCard>
      )}

      {scr && workflow?.workflow_name === "code-review-only" && (
        <ScanResultsView
          scr={{ ...scr, top_findings: allFindings.length ? allFindings : scr.top_findings }}
          cma={cma}
          reporting={reporting}
          workflowId={params.id}
          completedAt={workflow?.completed_at ?? output?.completed_at}
          startedAt={workflow?.started_at}
        />
      )}

      {scr && workflow?.workflow_name !== "code-review-only" && (
        <ScanResultsView
          scr={scr}
          cma={cma}
          reporting={reporting}
          workflowId={params.id}
          completedAt={workflow?.completed_at ?? output?.completed_at}
          startedAt={workflow?.started_at}
        />
      )}

      {(workflow?.status === "COMPLETED" || workflow?.status === "PAUSED") && !output && !loading && (
        <p className="t-muted">Workflow finished but output is not available yet.</p>
      )}
    </div>
  );
}
