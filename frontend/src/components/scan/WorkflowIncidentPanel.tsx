"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { fetchWorkflowOutput, fetchWorkflows, type WorkflowSummary } from "@/lib/workflows-api";
import { parseScrSnapshot, type ScrSnapshot } from "@/lib/scr-parse";

type TriageItem = {
  finding_id: string;
  severity: string;
  title: string;
  file_path: string;
  workflow_id: string;
  completed_at?: string;
};

export function WorkflowIncidentPanel() {
  const { token, tenantId, ready } = useAuth();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Record<string, ScrSnapshot>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token || !tenantId) return;
    setLoading(true);
    try {
      const list = await fetchWorkflows(tenantId, token, { limit: 30 });
      const codeReviews = list.filter(
        (w) => w.workflow_name === "code-review-only" && w.status === "COMPLETED"
      );
      setWorkflows(codeReviews);
      if (codeReviews.length && !selected) setSelected(codeReviews[0].workflow_id);

      const snaps: Record<string, ScrSnapshot> = {};
      await Promise.all(
        codeReviews.slice(0, 10).map(async (w) => {
          try {
            const out = await fetchWorkflowOutput(tenantId, w.workflow_id, token);
            if (out?.snapshot) {
              snaps[w.workflow_id] = out.snapshot as Record<string, ScrSnapshot>;
            }
          } catch {
            /* skip */
          }
        })
      );
      setSnapshot(snaps);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId, selected]);

  useEffect(() => {
    if (!ready) return;
    load();
  }, [ready, load]);

  const activeSnap = selected ? snapshot[selected] : undefined;
  const scr = activeSnap?.scr as ScrSnapshot | undefined;
  const cma = activeSnap?.cma as ScrSnapshot | undefined;
  const reporting = activeSnap?.reporting as ScrSnapshot | undefined;
  const parsed = parseScrSnapshot(scr);
  const triage: TriageItem[] = parsed.findings
    .filter((f) => ["CRITICAL", "HIGH"].includes(String(f.severity).toUpperCase()))
    .map((f) => ({
      finding_id: String(f.finding_id ?? f.file_path),
      severity: String(f.severity ?? "HIGH"),
      title: `${f.category} in ${f.file_path}`,
      file_path: String(f.file_path ?? ""),
      workflow_id: selected ?? "",
    }));

  const wf = workflows.find((w) => w.workflow_id === selected);
  const affected = new Set<string>();
  parsed.findings.forEach((f) => (f.reachable_from ?? []).forEach((r) => affected.add(r)));

  if (loading) {
    return (
      <div className="ac-card" style={{ padding: 24, opacity: 0.5 }}>
        Loading incident data from completed scans…
      </div>
    );
  }

  if (!workflows.length) {
    return (
      <div className="ac-card" style={{ padding: 24 }}>
        <p className="t-muted" style={{ margin: 0 }}>
          No completed code-review workflows yet. Run a scan from Connected Repos to populate incident data.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="ac-card" style={{ padding: 16 }}>
        <label className="eyebrow">Workflow</label>
        <select
          className="input"
          value={selected ?? ""}
          onChange={(e) => setSelected(e.target.value)}
          style={{ marginTop: 8, maxWidth: 420 }}
        >
          {workflows.map((w) => (
            <option key={w.workflow_id} value={w.workflow_id}>
              {w.workflow_id} · {w.completed_at ? new Date(w.completed_at).toLocaleString() : w.status}
            </option>
          ))}
        </select>
      </div>

      <div className="sub-grid-2">
        <div className="card">
          <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
            Incident timeline
          </div>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, fontSize: 12 }}>
            {wf?.started_at ? (
              <li style={{ marginBottom: 8 }}>
                Scan started — {new Date(wf.started_at).toLocaleString()}
              </li>
            ) : null}
            {scr?.completed_at ? (
              <li style={{ marginBottom: 8 }}>
                SCR completed — {new Date(String(scr.completed_at)).toLocaleString()} · risk {String(scr.risk_score)}
              </li>
            ) : null}
            {cma?.completed_at ? (
              <li style={{ marginBottom: 8 }}>
                Compliance mapping — {new Date(String(cma.completed_at)).toLocaleString()}
              </li>
            ) : null}
            {reporting?.completed_at ? (
              <li style={{ marginBottom: 8 }}>
                Report generated — {new Date(String(reporting.completed_at)).toLocaleString()}
              </li>
            ) : null}
          </ul>
        </div>

        <div className="card">
          <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
            Correlation
          </div>
          {scr?.correlated_to_incident ? (
            <p style={{ fontSize: 12 }}>Linked to active incident context.</p>
          ) : (
            <p className="t-muted" style={{ fontSize: 12 }}>
              No correlated incidents detected.
            </p>
          )}
        </div>
      </div>

      <div className="card">
        <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
          Triage queue ({triage.length})
        </div>
        {scr?.requires_human_approval ? (
          <p style={{ fontSize: 12, color: "var(--r-sec1)", marginBottom: 12 }}>
            Human approval required — review findings below.
          </p>
        ) : null}
        {triage.length === 0 ? (
          <p className="t-muted" style={{ fontSize: 12 }}>
            No critical/high findings requiring triage.
          </p>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {triage.slice(0, 15).map((item) => (
              <li
                key={item.finding_id}
                style={{
                  padding: "10px 0",
                  borderBottom: "1px solid var(--border-default)",
                  fontSize: 12,
                }}
              >
                <strong style={{ color: item.severity === "CRITICAL" ? "var(--r-sec1)" : "#ea580c" }}>
                  {item.severity}
                </strong>{" "}
                {item.title}
                <div className="t-muted mono" style={{ fontSize: 10, marginTop: 4 }}>
                  {item.file_path}
                </div>
              </li>
            ))}
          </ul>
        )}
        {selected ? (
          <Link href={`/workflows/${selected}`} className="btn btn-primary" style={{ marginTop: 12, display: "inline-block" }}>
            Open full scan results
          </Link>
        ) : null}
      </div>

      <div className="card">
        <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
          Affected systems / entry points
        </div>
        {affected.size ? (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
            {Array.from(affected).map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        ) : (
          <p className="t-muted" style={{ fontSize: 12 }}>
            No reachable entry points identified in findings.
          </p>
        )}
      </div>
    </div>
  );
}
