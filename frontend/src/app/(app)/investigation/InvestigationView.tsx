"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import {
  addInvestigationNote,
  fetchInvestigationCase,
  fetchInvestigationCases,
} from "@/lib/api";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { HITLQueuePanel } from "@/components/admin-center/HITLQueuePanel";
import { WorkflowIncidentPanel } from "@/components/scan/WorkflowIncidentPanel";

type Tab = "hitl" | "cases" | "scans";

type CaseSummary = { id: string; title: string; severity?: string };

type Note = { author: string; text: string; ts?: string };

type Ioc = { type: string; value: string; malicious?: boolean };

export function InvestigationView() {
  const searchParams = useSearchParams();
  const initialTab =
    searchParams.get("tab") === "cases"
      ? "cases"
      : searchParams.get("tab") === "scans"
        ? "scans"
        : "hitl";
  const { token, tenantId, ready, email } = useAuth();
  const [tab, setTab] = useState<Tab>(initialTab);
  const [hitlCount, setHitlCount] = useState(0);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);
  const [caseData, setCaseData] = useState<{
    title?: string;
    severity?: string;
    notes?: Note[];
    evidence_chain?: Array<{ id: string; title: string; agent_id: string; severity: string }>;
    kill_chain?: { stages: string[]; completed: string[]; progress_pct: number };
    iocs?: Ioc[];
    timeline?: Array<{ event?: string; text?: string; type?: string }>;
  }>({});

  useEffect(() => {
    const t = searchParams.get("tab");
    setTab(t === "cases" ? "cases" : t === "scans" ? "scans" : "hitl");
  }, [searchParams]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchInvestigationCases(tenantId, token)
      .then((list) => {
        setCases(list);
        if (list.length) setCaseId(list[0].id);
      })
      .catch(() => {});
  }, [ready, token, tenantId]);

  const reloadCase = useCallback(() => {
    if (!token || !caseId) return;
    fetchInvestigationCase(caseId, token).then(setCaseData).catch(() => {});
  }, [token, caseId]);

  useEffect(() => {
    if (!ready || !token || !caseId || tab !== "cases") return;
    reloadCase();
  }, [ready, token, caseId, tab, reloadCase]);

  const stages = caseData.kill_chain?.stages ?? [];
  const completed = new Set(caseData.kill_chain?.completed ?? []);
  const progress = caseData.kill_chain?.progress_pct ?? 0;
  const evidenceChain = caseData.evidence_chain ?? [];
  const notes = caseData.notes ?? [];
  const iocs = caseData.iocs ?? [];

  const onAddNote = async () => {
    if (!token || !caseId || !note.trim()) return;
    setNoteBusy(true);
    try {
      await addInvestigationNote(caseId, token, note.trim());
      toast.success("Note added");
      setNote("");
      reloadCase();
    } catch {
      toast.error("Failed to add note");
    } finally {
      setNoteBusy(false);
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Incident Response"
        subtitle={
          tab === "hitl"
            ? `${hitlCount} action${hitlCount === 1 ? "" : "s"} awaiting analyst approval`
            : caseData.title
              ? `${caseData.title} · ${caseData.severity ?? "open"}`
              : "Investigation cases and kill chain analysis"
        }
        toolbar={
          cases.length > 1 && tab === "cases" ? (
            <select
              className="ac-form-control"
              value={caseId ?? ""}
              onChange={(e) => setCaseId(e.target.value)}
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          ) : undefined
        }
      />

      <div className="ac-filter-wrap" style={{ marginBottom: 16 }}>
        <button
          type="button"
          className={`ac-filter-btn${tab === "hitl" ? " is-active" : ""}`}
          onClick={() => setTab("hitl")}
        >
          HITL Approval {hitlCount > 0 ? `(${hitlCount})` : ""}
        </button>
        <button
          type="button"
          className={`ac-filter-btn${tab === "scans" ? " is-active" : ""}`}
          onClick={() => setTab("scans")}
        >
          Code review incidents
        </button>
        <button
          type="button"
          className={`ac-filter-btn${tab === "cases" ? " is-active" : ""}`}
          onClick={() => setTab("cases")}
        >
          Investigation Cases
        </button>
      </div>

      {tab === "hitl" ? (
        <HITLQueuePanel onQueueChange={setHitlCount} />
      ) : tab === "scans" ? (
        <WorkflowIncidentPanel />
      ) : (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="eyebrow">Kill chain progress</div>
            <div className="hitl-kill-chain">
              <div className="hitl-kill-chain-track">
                <div className="hitl-kill-chain-fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="hitl-kill-chain-stages">
                {stages.map((s, i) => {
                  const done = completed.has(s);
                  return (
                    <div key={s} className="hitl-kill-chain-stage">
                      <div className={`hitl-stage-dot${done ? " is-done" : ""}`}>{done ? "✓" : i + 1}</div>
                      <span className="mono t-muted" style={{ fontSize: 9 }}>
                        {s}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="sub-grid-2">
            <div className="card">
              <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
                Evidence chain
              </div>
              {evidenceChain.length ? (
                <ul className="hitl-evidence-list">
                  {evidenceChain.map((item) => (
                    <li key={item.id} className="hitl-evidence-item">
                      <span className="mono" style={{ fontSize: 10, color: "var(--purple-mid)" }}>
                        {item.agent_id}
                      </span>
                      <span className="t-title" style={{ fontSize: 12, display: "block" }}>
                        {item.title}
                      </span>
                      <span className="mono t-muted" style={{ fontSize: 10 }}>
                        {item.severity}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="t-muted" style={{ fontSize: 12 }}>
                  No linked findings
                </p>
              )}

              <div className="eyebrow" style={{ marginTop: 16, marginBottom: 8 }}>
                Analyst notes
              </div>
              {notes.length ? (
                <ul className="hitl-notes-list">
                  {notes.map((n, i) => (
                    <li key={`${n.ts ?? i}-${n.text.slice(0, 20)}`} className="hitl-note-item">
                      <span className="mono t-muted" style={{ fontSize: 10 }}>
                        {n.author}
                        {n.ts ? ` · ${new Date(n.ts).toLocaleString()}` : ""}
                      </span>
                      <p style={{ fontSize: 12, margin: "4px 0 0", color: "var(--text-secondary)" }}>
                        {n.text}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="t-muted" style={{ fontSize: 11, marginBottom: 8 }}>
                  No notes yet — add context for handoff or audit trail.
                </p>
              )}

              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add analyst note…"
                  className="ac-form-control"
                  style={{ flex: 1, borderRadius: 8 }}
                  onKeyDown={(e) => e.key === "Enter" && onAddNote()}
                />
                <button type="button" className="btn-accent" disabled={noteBusy || !note.trim()} onClick={onAddNote}>
                  {noteBusy ? "…" : "Add"}
                </button>
              </div>
              <p className="t-muted mono" style={{ fontSize: 10, marginTop: 6 }}>
                Signed as {email ?? "analyst"}
              </p>
            </div>

            <div className="card">
              <div className="t-title" style={{ fontSize: 13, marginBottom: 10 }}>
                Extracted IOCs
              </div>
              {iocs.length ? (
                <ul className="hitl-ioc-list">
                  {iocs.map((ioc) => (
                    <li key={`${ioc.type}-${ioc.value}`} className="hitl-ioc-item">
                      <span className="mono t-muted">{ioc.type}</span>
                      <span className="mono t-title">{ioc.value}</span>
                      {ioc.malicious ? (
                        <span style={{ color: "var(--r-sec2)", fontSize: 10, fontWeight: 700 }}>MALICIOUS</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="t-muted" style={{ fontSize: 12 }}>
                  No IOCs extracted from case evidence yet.
                </p>
              )}

              <div className="eyebrow" style={{ marginTop: 16, marginBottom: 6 }}>
                Timeline
              </div>
              <ul className="hitl-timeline-list">
                {(caseData.timeline ?? [])
                  .filter((e) => e.type !== "note")
                  .map((e, i) => (
                    <li key={i} className="t-muted" style={{ fontSize: 11, marginBottom: 6 }}>
                      {e.event ?? e.text}
                    </li>
                  ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </>
  );
}
