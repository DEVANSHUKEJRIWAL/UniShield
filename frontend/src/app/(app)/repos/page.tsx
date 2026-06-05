"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { GitBranch, Link2, RefreshCw, Shield, Trash2 } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { useAuth } from "@/lib/auth";
import {
  connectRepo,
  deleteRepo,
  fetchRepos,
  scanRepo,
  verifyRepo,
  type RepoConnection,
  type VCSProvider,
} from "@/lib/repos-api";
import { fetchWorkflowDefinitions, type WorkflowDefinition } from "@/lib/workflows-api";

const PROVIDERS: { id: VCSProvider; label: string }[] = [
  { id: "github", label: "GitHub" },
  { id: "gitlab", label: "GitLab" },
  { id: "bitbucket", label: "Bitbucket" },
];

const STATUS_COLOR: Record<string, string> = {
  connected: "var(--green)",
  pending: "var(--amber)",
  auth_failed: "var(--r-sec1)",
  not_found: "var(--r-sec1)",
  rate_limited: "var(--amber)",
};

export default function ReposPage() {
  const router = useRouter();
  const { token, tenantId, email, ready } = useAuth();
  const [repos, setRepos] = useState<RepoConnection[]>([]);
  const [definitions, setDefinitions] = useState<Record<string, WorkflowDefinition>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [provider, setProvider] = useState<VCSProvider>("github");
  const [repoUrl, setRepoUrl] = useState("");
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("");
  const [patToken, setPatToken] = useState("");
  const [description, setDescription] = useState("");
  const [isCrownJewel, setIsCrownJewel] = useState(false);
  const [scanWorkflowId, setScanWorkflowId] = useState("code-review-only");

  const refresh = useCallback(async () => {
    if (!token || !tenantId) return;
    setLoading(true);
    try {
      const [repoList, defs] = await Promise.all([
        fetchRepos(tenantId, token),
        fetchWorkflowDefinitions(token).catch((): Record<string, WorkflowDefinition> => ({})),
      ]);
      setRepos(repoList);
      setDefinitions(defs);
      setScanWorkflowId((current) => {
        if (current && defs[current]) return current;
        if (defs["code-review-only"]) return "code-review-only";
        return Object.keys(defs)[0] ?? current;
      });
    } catch (e) {
      toast.error("Failed to load repositories", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  }, [token, tenantId]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    refresh();
  }, [ready, token, tenantId, refresh]);

  const parseRepoUrl = (url: string) => {
    try {
      const parsed = new URL(url.trim());
      const parts = parsed.pathname.replace(/^\//, "").replace(/\.git$/, "").split("/");
      if (parts.length >= 2) {
        setRepoOwner(parts[0]);
        setRepoName(parts[1]);
      }
    } catch {
      /* user may fill owner/name manually */
    }
  };

  const handleConnect = async () => {
    if (!token || !tenantId || !email) return;
    if (!repoUrl || !repoOwner || !repoName || !patToken) {
      toast.error("Fill in repository URL, owner, name, and access token");
      return;
    }
    setSubmitting(true);
    try {
      await connectRepo(token, {
        connection: {
          client_id: tenantId,
          provider,
          repo_url: repoUrl,
          repo_owner: repoOwner,
          repo_name: repoName,
          default_branch: defaultBranch || "main",
          description: description || undefined,
          is_crown_jewel: isCrownJewel,
          registered_by: email,
        },
        token: patToken,
      });
      toast.success("Repository connected");
      setPatToken("");
      setShowForm(false);
      refresh();
    } catch (e) {
      toast.error("Connect failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (connectionId: string) => {
    if (!token || !tenantId) return;
    try {
      await verifyRepo(tenantId, connectionId, token);
      toast.success("Connection verified");
      refresh();
    } catch (e) {
      toast.error("Verification failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    }
  };

  const handleDelete = async (connectionId: string) => {
    if (!token || !tenantId) return;
    try {
      await deleteRepo(tenantId, connectionId, token);
      toast.success("Repository removed");
      refresh();
    } catch (e) {
      toast.error("Delete failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    }
  };

  const handleScan = async (connectionId: string) => {
    if (!token || !tenantId) return;
    try {
      const result = await scanRepo(tenantId, connectionId, token, {
        workflow_id: scanWorkflowId,
      });
      toast.success("Scan started", {
        description: `${result.workflow_id} — tracking progress`,
      });
      refresh();
      router.push(`/workflows/${result.workflow_id}`);
    } catch (e) {
      toast.error("Scan failed", {
        description: e instanceof Error ? e.message : "Unknown error",
      });
    }
  };

  return (
    <div className="ac-page">
      <AdminPageHeader
        title="Connected Repositories"
        subtitle="Register GitHub, GitLab, or Bitbucket repos for SCR workflows and attack-path analysis"
        toolbar={
          <>
            <button type="button" className="btn btn-ghost" onClick={refresh} disabled={loading}>
              <RefreshCw style={{ width: 14, height: 14, marginRight: 6 }} />
              Refresh
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
              <Link2 style={{ width: 14, height: 14, marginRight: 6 }} />
              Connect repo
            </button>
          </>
        }
      />

      {showForm && (
        <div style={{ marginBottom: 20 }}>
          <AnimatedCard className="ac-card">
          <h3 className="t-title" style={{ fontSize: 15, margin: "0 0 12px" }}>
            Connect repository
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Provider
              <select
                className="input"
                value={provider}
                onChange={(e) => setProvider(e.target.value as VCSProvider)}
              >
                {PROVIDERS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Default branch
              <input
                className="input"
                placeholder="Auto-detect from GitHub (recommended)"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, gridColumn: "1 / -1" }}>
              Repository URL
              <input
                className="input"
                placeholder="https://github.com/org/repo"
                value={repoUrl}
                onChange={(e) => {
                  setRepoUrl(e.target.value);
                  parseRepoUrl(e.target.value);
                }}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Owner
              <input className="input" value={repoOwner} onChange={(e) => setRepoOwner(e.target.value)} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
              Name
              <input className="input" value={repoName} onChange={(e) => setRepoName(e.target.value)} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, gridColumn: "1 / -1" }}>
              Personal access token
              <input
                className="input"
                type="password"
                autoComplete="off"
                value={patToken}
                onChange={(e) => setPatToken(e.target.value)}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, gridColumn: "1 / -1" }}>
              Description (optional)
              <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
              <input type="checkbox" checked={isCrownJewel} onChange={(e) => setIsCrownJewel(e.target.checked)} />
              Mark as crown jewel repository
            </label>
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-primary" disabled={submitting} onClick={handleConnect}>
              {submitting ? "Connecting…" : "Save connection"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </AnimatedCard>
        </div>
      )}

      <AnimatedCard className="ac-card">
        {loading && <p className="t-muted">Loading repositories…</p>}
        {!loading && repos.length === 0 && (
          <p className="t-muted">No repositories connected yet. Use Connect repo to register one.</p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {repos.map((repo) => (
            <div
              key={repo.connection_id}
              className="ac-list-row"
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto auto auto auto",
                gap: 12,
                alignItems: "center",
                padding: "12px 14px",
                borderRadius: 10,
                border: "1px solid var(--border-default)",
                background: "var(--bg-surface)",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <GitBranch style={{ width: 14, height: 14, opacity: 0.6 }} />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>
                    {repo.repo_owner}/{repo.repo_name}
                  </span>
                  {repo.is_crown_jewel && (
                    <span title="Crown jewel">
                      <Shield style={{ width: 14, height: 14, color: "var(--amber)" }} />
                    </span>
                  )}
                </div>
                <p className="mono t-muted" style={{ margin: "4px 0 0", fontSize: 11 }}>
                  {repo.provider} · {repo.default_branch}
                  {repo.last_scanned_at ? ` · scanned ${new Date(repo.last_scanned_at).toLocaleDateString()}` : ""}
                </p>
              </div>
              <span
                className="mono"
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: STATUS_COLOR[repo.status] ?? "var(--m3)",
                }}
              >
                {repo.status}
              </span>
              <button type="button" className="btn btn-ghost" onClick={() => handleVerify(repo.connection_id)}>
                Verify
              </button>
              <button type="button" className="btn btn-primary" onClick={() => handleScan(repo.connection_id)}>
                Scan
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => handleDelete(repo.connection_id)}>
                <Trash2 style={{ width: 14, height: 14 }} />
              </button>
            </div>
          ))}
        </div>

        {repos.length > 0 && Object.keys(definitions).length > 0 && (
          <p className="t-muted" style={{ marginTop: 16, fontSize: 12 }}>
            Scans use workflow:{" "}
            <select
              className="input"
              style={{ display: "inline-block", width: "auto", marginLeft: 6 }}
              value={scanWorkflowId}
              onChange={(e) => setScanWorkflowId(e.target.value)}
            >
              {Object.entries(definitions).map(([id, def]) => (
                <option key={id} value={id}>
                  {def.label}
                </option>
              ))}
            </select>
          </p>
        )}
      </AnimatedCard>
    </div>
  );
}
