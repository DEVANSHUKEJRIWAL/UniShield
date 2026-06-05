"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GitBranch, Play, RefreshCw, Sparkles } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { useAuth } from "@/lib/auth";
import { useWorkflowList } from "@/hooks/useWorkflows";
import { fetchRepos, scanRepo, type RepoConnection } from "@/lib/repos-api";
import {
  fetchWorkflowDefinitions,
  fetchWorkflowHealth,
  triggerDemoScan,
  triggerWorkflow,
  type WorkflowDefinition,
} from "@/lib/workflows-api";

const STATUS_STYLE: Record<string, string> = {
  RUNNING: "var(--violet)",
  COMPLETED: "var(--green)",
  FAILED: "var(--r-sec1)",
  PAUSED: "var(--amber)",
};

export default function WorkflowsPage() {
  const router = useRouter();
  const { token, tenantId, ready } = useAuth();
  const { workflows, loading, error, refresh } = useWorkflowList();
  const [definitions, setDefinitions] = useState<Record<string, WorkflowDefinition>>({});
  const [repos, setRepos] = useState<RepoConnection[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [orchestratorOk, setOrchestratorOk] = useState<boolean | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [demoStarting, setDemoStarting] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchWorkflowHealth(token)
      .then((h) => setOrchestratorOk(h.reachable))
      .catch(() => setOrchestratorOk(false));
    fetchWorkflowDefinitions(token)
      .then(setDefinitions)
      .catch(() => setDefinitions({}));
    fetchRepos(tenantId, token)
      .then((list) => {
        setRepos(list);
        if (list.length > 0) setSelectedRepoId(list[0].connection_id);
      })
      .catch(() => setRepos([]));
  }, [ready, token, tenantId]);

  const filtered =
    filter === "all" ? workflows : workflows.filter((w) => w.status === filter);

  const runWorkflow = async (workflowId: string) => {
    if (!token || !tenantId) return;
    setTriggering(workflowId);
    try {
      if (selectedRepoId) {
        const result = await scanRepo(tenantId, selectedRepoId, token, { workflow_id: workflowId });
        toast.success("Workflow started from connected repo", { description: result.workflow_id });
      } else {
        const result = await triggerWorkflow(tenantId, token, {
          workflow_id: workflowId,
          repo_url: "https://github.com/DEVANSHUKEJRIWAL/UniShield",
          repo_ref: "main",
        });
        toast.success("Workflow started", { description: result.workflow_id });
      }
      refresh();
    } catch (e) {
      toast.error("Failed to start workflow", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setTriggering(null);
    }
  };

  const runDemoScan = async () => {
    if (!token || !tenantId) return;
    setDemoStarting(true);
    try {
      const result = await triggerDemoScan(tenantId, token, "code-review-only");
      toast.success("Demo scan started", {
        description: `Scanning local workspace — ${result.workflow_id}`,
      });
      refresh();
      router.push(`/workflows/${result.workflow_id}`);
    } catch (e) {
      toast.error("Demo scan failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setDemoStarting(false);
    }
  };

  const selectedRepo = repos.find((r) => r.connection_id === selectedRepoId);

  return (
    <div className="ac-page">
      <AdminPageHeader
        title="Security Workflows"
        subtitle="OpenClaw orchestrator — SCR, compliance mapping, and reporting pipelines"
        toolbar={
          <>
            <button
              type="button"
              className="btn btn-primary"
              disabled={demoStarting || orchestratorOk === false}
              onClick={runDemoScan}
            >
              <Sparkles style={{ width: 14, height: 14, marginRight: 6 }} />
              {demoStarting ? "Starting…" : "Demo scan"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={refresh} disabled={loading}>
              <RefreshCw style={{ width: 14, height: 14, marginRight: 6 }} />
              Refresh
            </button>
          </>
        }
      />

      {orchestratorOk === false && (
        <div style={{ marginBottom: 16 }}>
          <AnimatedCard className="ac-card">
            <p className="t-muted" style={{ margin: 0, fontSize: 13 }}>
              Workflow orchestrator unreachable. Start it with{" "}
              <code>./scripts/run-orchestrator.sh</code> (port 8001).
            </p>
          </AnimatedCard>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <AnimatedCard className="ac-card">
        <p className="t-muted" style={{ margin: "0 0 12px", fontSize: 12 }}>
          Use <strong>Demo scan</strong> to run the full SCR → CMA → Reporting pipeline on this
          workspace without connecting a Git repo. Connect a repo for production scans.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
            Target repository
            <select
              className="input"
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              style={{ minWidth: 220 }}
            >
              <option value="">Manual repo URL (fallback)</option>
              {repos.map((repo) => (
                <option key={repo.connection_id} value={repo.connection_id}>
                  {repo.repo_owner}/{repo.repo_name} ({repo.default_branch})
                </option>
              ))}
            </select>
          </label>
          {selectedRepo && (
            <span className="mono t-muted" style={{ fontSize: 11 }}>
              {selectedRepo.repo_url}
            </span>
          )}
          {repos.length === 0 && (
            <Link href="/repos" className="btn btn-ghost" style={{ fontSize: 12 }}>
              Connect a repo
            </Link>
          )}
        </div>
        </AnimatedCard>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        {Object.entries(definitions).map(([id, def]) => (
          <AnimatedCard key={id} className="ac-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 className="t-title" style={{ fontSize: 15, margin: "0 0 4px" }}>
                  {def.label}
                </h3>
                <p className="t-muted" style={{ margin: 0, fontSize: 12 }}>
                  {def.description}
                </p>
                <p className="mono t-muted" style={{ margin: "8px 0 0", fontSize: 11 }}>
                  ~{def.estimated_minutes} min · {def.steps.length} steps
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={triggering === id || orchestratorOk === false}
                onClick={() => runWorkflow(id)}
              >
                <Play style={{ width: 14, height: 14, marginRight: 4 }} />
                {triggering === id ? "Starting…" : "Run"}
              </button>
            </div>
          </AnimatedCard>
        ))}
      </div>

      <AnimatedCard className="ac-card">
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          {["all", "RUNNING", "COMPLETED", "FAILED", "PAUSED"].map((s) => (
            <button
              key={s}
              type="button"
              className={`btn ${filter === s ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setFilter(s)}
            >
              {s === "all" ? "All" : s}
            </button>
          ))}
        </div>

        {loading && <p className="t-muted">Loading workflows…</p>}
        {error && <p style={{ color: "var(--r-sec1)" }}>{error}</p>}
        {!loading && !error && filtered.length === 0 && (
          <p className="t-muted">No workflows yet. Run a pipeline above.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {filtered.map((wf) => (
            <Link
              key={wf.workflow_id}
              href={`/workflows/${wf.workflow_id}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <div
                className="ac-list-row"
                style={{
                  display: "grid",
                  gridTemplateColumns: "140px 1fr auto auto",
                  gap: 12,
                  alignItems: "center",
                  padding: "12px 14px",
                  borderRadius: 10,
                  border: "1px solid var(--border-default)",
                  background: "var(--bg-surface)",
                }}
              >
                <span className="mono" style={{ fontWeight: 700, fontSize: 12 }}>
                  {wf.workflow_id}
                </span>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{wf.workflow_name}</span>
                  <div className="mono t-muted" style={{ fontSize: 11, marginTop: 4 }}>
                    {Object.entries(wf.agent_states)
                      .map(([a, s]) => `${a}:${s}`)
                      .join(" · ")}
                  </div>
                </div>
                <span
                  className="mono"
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: STATUS_STYLE[wf.status] ?? "var(--m3)",
                  }}
                >
                  {wf.status}
                </span>
                <GitBranch style={{ width: 14, height: 14, opacity: 0.5 }} />
              </div>
            </Link>
          ))}
        </div>
      </AnimatedCard>
    </div>
  );
}
