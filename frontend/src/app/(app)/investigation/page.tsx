"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/auth";
import { fetchInvestigationCase, fetchInvestigationCases } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { RiskGauge } from "@/components/ui/RiskGauge";

const STAGES = ["Initial Access", "Execution", "Persistence", "Privilege Escalation", "Lateral Movement", "Exfiltration"];

type Ioc = { type: string; value: string; malicious?: boolean };

export default function InvestigationPage() {
  const { token, tenantId, ready } = useAuth();
  const [caseId, setCaseId] = useState<string | null>(null);
  const [caseData, setCaseData] = useState<{
    title?: string;
    severity?: string;
    timeline?: Array<{ event?: string; text?: string; type?: string }>;
    evidence?: Array<{ agent?: string; type?: string }>;
    iocs?: Ioc[];
  }>({});

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchInvestigationCases(tenantId, token)
      .then((cases) => {
        if (cases.length) setCaseId(cases[0].id);
      })
      .catch(() => {});
  }, [ready, token, tenantId]);

  useEffect(() => {
    if (!ready || !token || !caseId) return;
    fetchInvestigationCase(caseId, token).then(setCaseData).catch(() => {});
  }, [ready, token, caseId]);

  const evidenceAgents = (caseData.evidence ?? []).map((e) => e.agent).filter(Boolean) as string[];
  const iocs = caseData.iocs ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Case Investigation</GradientText></h1>
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
            animate={{ width: "75%" }}
            transition={{ duration: 1.5, ease: "easeOut" }}
          />
          {STAGES.map((s, i) => (
            <motion.div key={s} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} className="relative z-10 flex flex-col items-center">
              <div className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold" style={{ background: i < 4 ? "var(--violet)" : "var(--bg-surface)", border: `2px solid ${i < 4 ? "var(--violet-light)" : "var(--border-default)"}` }}>
                {i < 4 ? "✓" : i + 1}
              </div>
              <p className="mt-2 max-w-[80px] text-center font-mono text-[8px] text-[var(--text-muted)]">{s}</p>
            </motion.div>
          ))}
        </div>
      </AnimatedCard>

      <div className="grid gap-6 lg:grid-cols-3">
        <AnimatedCard delay={0.2} className="lg:col-span-1">
          <h3 className="mb-4 font-bold">Agent Evidence</h3>
          {(evidenceAgents.length ? evidenceAgents : ["dark-web-agent", "forensics-agent"]).map((agent, i) => (
            <motion.div key={agent} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }} className="mb-3 rounded-xl border border-[var(--border-subtle)] p-3">
              <p className="font-mono text-xs text-[var(--violet-light)]">{agent}</p>
            </motion.div>
          ))}
          <TypewriterText text={(caseData.timeline ?? [])[0]?.event ?? "Awaiting case timeline..."} />
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
            <RiskGauge score={caseData.severity === "critical" ? 88 : 65} size="md" label="Case Risk" />
          </div>
        </AnimatedCard>
      </div>
    </div>
  );
}
