"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { fetchAttckMapping, fetchCompliance, generateComplianceReport } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";

const FRAMEWORKS = ["RBI_IT_FRAMEWORK_2023", "SEBI_CSCRF", "DPDP_ACT_2023", "PCI_DSS_V4", "NIST_CSF_2", "ISO_27001_2022"];

const STATUS_COLORS = {
  implemented: "var(--green)",
  partial: "var(--amber)",
  gap: "var(--red)",
  "not assessed": "var(--text-muted)",
};

export default function CompliancePage() {
  const { token, tenantId, ready } = useAuth();
  const [framework, setFramework] = useState("NIST_CSF_2");
  const [data, setData] = useState<{ coverage_pct?: number; controls?: Array<{ id: string; title: string; status: keyof typeof STATUS_COLORS; mitre?: string[] }> }>({});
  const [techniques, setTechniques] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchCompliance(tenantId, framework, token).then(setData).catch(() => {});
    fetchAttckMapping(tenantId, framework, token)
      .then((d) => setTechniques(d.techniques ?? []))
      .catch(() => {});
  }, [ready, token, tenantId, framework]);

  const score = Math.round((data.coverage_pct ?? 0.78) * 100);
  const controls = data.controls ?? [];

  const onGenerate = async () => {
    if (!token || !tenantId) return;
    setGenerating(true);
    try {
      const result = await generateComplianceReport(tenantId, framework, token);
      toast.success("Compliance report generated", { description: `Coverage ${Math.round((result.coverage_pct ?? 0) * 100)}%` });
    } catch {
      toast.error("Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-extrabold"><GradientText>Compliance War Room</GradientText></h1>
        <button
          disabled={generating}
          onClick={onGenerate}
          className="rounded bg-[var(--violet)] px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Report"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {FRAMEWORKS.map((fw) => (
          <motion.button
            key={fw}
            onClick={() => setFramework(fw)}
            whileTap={{ scale: 0.95 }}
            className="rounded-lg px-3 py-1.5 text-[11px] font-mono font-bold"
            style={{
              background: framework === fw ? "var(--violet-dim)" : "var(--bg-surface)",
              color: framework === fw ? "var(--violet-light)" : "var(--text-secondary)",
              border: `1px solid ${framework === fw ? "rgba(124,58,237,0.3)" : "var(--border-subtle)"}`,
            }}
          >
            {fw.replace(/_/g, " ")}
          </motion.button>
        ))}
      </div>

      <div className="flex flex-col items-center gap-8 md:flex-row">
        <AnimatedCard className="flex flex-col items-center p-8">
          <div className="relative">
            <svg width={160} height={160} className="-rotate-90">
              <circle cx={80} cy={80} r={70} fill="none" stroke="var(--border-default)" strokeWidth={10} />
              <motion.circle
                cx={80}
                cy={80}
                r={70}
                fill="none"
                stroke={score > 70 ? "var(--green)" : score > 50 ? "var(--amber)" : "var(--red)"}
                strokeWidth={10}
                strokeLinecap="round"
                strokeDasharray={440}
                initial={{ strokeDashoffset: 440 }}
                animate={{ strokeDashoffset: 440 - (score / 100) * 440 }}
                transition={{ duration: 1.5 }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-extrabold" style={{ fontFamily: "var(--font-display)" }}>
                <CountUp end={score} duration={2} />%
              </span>
              <span className="font-mono text-[10px] text-[var(--text-muted)]">COVERAGE</span>
            </div>
          </div>
        </AnimatedCard>

        <AnimatedCard className="flex-1">
          <h2 className="mb-4 font-bold">Control Heatmap</h2>
          <div className="grid grid-cols-3 gap-2 md:grid-cols-6">
            {controls.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.02 }}
                whileHover={{ scale: 1.1, zIndex: 10 }}
                title={`${c.id}: ${c.title}${c.mitre?.length ? ` · MITRE ${c.mitre.join(", ")}` : ""}`}
                className="aspect-square cursor-pointer rounded-lg p-2 text-center"
                style={{
                  background: `color-mix(in srgb, ${STATUS_COLORS[c.status]} 20%, var(--bg-tertiary))`,
                  border: `1px solid ${STATUS_COLORS[c.status]}`,
                }}
              >
                <p className="font-mono text-[10px] font-bold">{c.id}</p>
                <p className="mt-1 text-[8px] capitalize text-[var(--text-muted)]">{c.status}</p>
              </motion.div>
            ))}
          </div>
        </AnimatedCard>
      </div>

      {techniques.length > 0 && (
        <AnimatedCard>
          <h2 className="mb-3 font-bold">ATT&CK Techniques (from findings)</h2>
          <div className="flex flex-wrap gap-2 font-mono text-xs">
            {techniques.map((t) => (
              <span key={t} className="rounded border border-[var(--border-subtle)] px-2 py-1">{t}</span>
            ))}
          </div>
        </AnimatedCard>
      )}
    </div>
  );
}
