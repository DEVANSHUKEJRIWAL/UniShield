"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import {
  addInvestigationNote,
  fetchInvestigationCase,
  fetchInvestigationCases,
} from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { RiskGauge } from "@/components/ui/RiskGauge";

type Ioc = { type: string; value: string; malicious?: boolean };

type CaseSummary = { id: string; title: string; severity?: string };

export default function InvestigationPage() {
  const { token, tenantId, ready } = useAuth();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [caseData, setCaseData] = useState<{
    title?: string;
    severity?: string;
    timeline?: Array<{ event?: string; text?: string; type?: string }>;
    evidence?: Array<{ agent?: string; type?: string }>;
    evidence_chain?: Array<{ id: string; title: string; agent_id: string; severity: string }>;
    kill_chain?: { stages: string[]; completed: string[]; progress_pct: number };
    iocs?: Ioc[];
  }>({});

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchInvestigationCases(tenantId, token)
      .then((list) => {
        setCases(list);
        if (list.length) setCaseId(list[0].id);
      })
      .catch(() => {});
  }, [ready, token, tenantId]);

  useEffect(() => {
    if (!ready || !token || !caseId) return;
    fetchInvestigationCase(caseId, token).then(setCaseData).catch(() => {});
  }, [ready, token, caseId]);

  const stages = caseData.kill_chain?.stages ?? [];
  const completed = new Set(caseData.kill_chain?.completed ?? []);
  const progress = caseData.kill_chain?.progress_pct ?? 0;
  const evidenceChain = caseData.evidence_chain ?? [];
  const iocs = caseData.iocs ?? [];

  const onAddNote = async () => {
    if (!token || !caseId || !note.trim()) return;
    try {
      await addInvestigationNote(caseId, token, note.trim());
      toast.success("Note added");
      setNote("");
      fetchInvestigationCase(caseId, token).then(setCaseData);
    } catch {
      toast.error("Failed to add note");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-extrabold"><GradientText>Case Investigation</GradientText></h1>
        {cases.length > 1 && (
          <select
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 font-mono text-xs"
            value={caseId ?? ""}
            onChange={(e) => setCaseId(e.target.value)}
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
        )}
      </div>
      {caseData.title && (
        <p className="font-mono text-sm text-[var(--text-muted)]">{caseData.title} · {caseData.severity}</p>
      )}

      <AnimatedCard>
        <h2 className="mb-6 font-mono text-xs uppercase tracking-widest text-[var(--text-muted)]">Kill Chain Timeline</h2>
        <div className="relative flex justify-between">
          <div className="absolute left-0 right-0 top-4 h-0.5 bg-[var(--border-default)]" />
          <motion.div
            className="absolute left-0 top-4 h-0.5 bg-gradient-to-r from-[var(--violet)] to-[var(--red)]"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 1.5, ease: "easeOut" }}
          />
          {stages.map((s, i) => {
            const done = completed.has(s);
            return (
              <motion.div key={s} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} className="relative z-10 flex flex-col items-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold" style={{ background: done ? "var(--violet)" : "var(--bg-surface)", border: `2px solid ${done ? "var(--violet-light)" : "var(--border-default)"}` }}>
                  {done ? "✓" : i + 1}
                </div>
                <p className="mt-2 max-w-[80px] text-center font-mono text-[8px] text-[var(--text-muted)]">{s}</p>
              </motion.div>
            );
          })}
        </div>
      </AnimatedCard>

      <div className="grid gap-6 lg:grid-cols-3">
        <AnimatedCard delay={0.2} className="lg:col-span-1">
          <h3 className="mb-4 font-bold">Evidence Chain</h3>
          {(evidenceChain.length ? evidenceChain : []).map((item, i) => (
            <motion.div key={item.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }} className="mb-3 rounded-xl border border-[var(--border-subtle)] p-3">
              <p className="font-mono text-xs text-[var(--violet-light)]">{item.agent_id}</p>
              <p className="text-xs">{item.title}</p>
              <p className="font-mono text-[10px] text-[var(--text-muted)]">{item.severity}</p>
            </motion.div>
          ))}
          {!evidenceChain.length && (
            <p className="font-mono text-xs text-[var(--text-muted)]">No linked findings yet</p>
          )}
          <TypewriterText text={(caseData.timeline ?? [])[0]?.event ?? (caseData.timeline ?? [])[0]?.text ?? "Awaiting case timeline..."} />
          <div className="mt-4 flex gap-2">
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add analyst note..."
              className="flex-1 rounded border border-[var(--border-subtle)] bg-transparent px-2 py-1 text-xs"
            />
            <button onClick={onAddNote} className="rounded bg-[var(--violet)] px-2 py-1 text-xs text-white">Add</button>
          </div>
        </AnimatedCard>

        <AnimatedCard delay={0.3} className="lg:col-span-2">
          <h3 className="mb-4 font-bold">Extracted IOCs</h3>
          <div className="space-y-2">
            {(iocs.length ? iocs : [{ type: "INFO", value: "No IOCs extracted yet", malicious: false }]).map((ioc, i) => (
              <motion.div key={`${ioc.type}-${ioc.value}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.08 }} className="flex items-center justify-between rounded-lg bg-[var(--bg-tertiary)] p-3 font-mono text-xs">
                <span className="text-[var(--text-muted)]">{ioc.type}</span>
                <span>{ioc.value}</span>
                {ioc.malicious && <span className="text-[var(--red)]">MALICIOUS</span>}
              </motion.div>
            ))}
          </div>
          <div className="mt-6 flex justify-center">
            <RiskGauge score={caseData.severity === "critical" ? 88 : progress || 65} size="md" label="Case Risk" />
          </div>
        </AnimatedCard>
      </div>
    </div>
  );
}
