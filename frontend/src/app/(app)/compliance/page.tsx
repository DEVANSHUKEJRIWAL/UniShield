"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import { useAuth } from "@/lib/auth";
import { fetchCompliance } from "@/lib/api";
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
  const { token, tenantId } = useAuth();
  const [framework, setFramework] = useState("NIST_CSF_2");
  const [data, setData] = useState<{ coverage_pct?: number; controls?: Array<{ id: string; title: string; status: keyof typeof STATUS_COLORS }> }>({});

  useEffect(() => {
    if (token && tenantId) fetchCompliance(tenantId, framework, token).then(setData).catch(() => {});
  }, [token, tenantId, framework]);

  const score = Math.round((data.coverage_pct ?? 0.78) * 100);
  const controls = data.controls ?? [
    { id: "AC-1", title: "Access Control Policy", status: "implemented" as const },
    { id: "AC-2", title: "Account Management", status: "partial" as const },
    { id: "IR-4", title: "Incident Handling", status: "implemented" as const },
    { id: "SI-4", title: "System Monitoring", status: "gap" as const },
    { id: "AU-2", title: "Audit Events", status: "implemented" as const },
    { id: "CM-3", title: "Config Change Control", status: "partial" as const },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Compliance War Room</GradientText></h1>

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
                title={`${c.id}: ${c.title}`}
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
    </div>
  );
}
