"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/auth";
import { fetchExecutiveDashboard } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";
import CountUp from "react-countup";

export default function ExecutiveDashboardPage() {
  const { token, tenantId } = useAuth();
  const [data, setData] = useState<{ risk_trend?: Array<{ date: string; score: number }>; critical_summary?: Array<{ title: string; severity: string }> }>({});

  useEffect(() => {
    if (token && tenantId) fetchExecutiveDashboard(tenantId, token).then(setData).catch(() => {});
  }, [token, tenantId]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Executive Overview</GradientText></h1>
      <div className="grid gap-6 md:grid-cols-2">
        <AnimatedCard>
          <h2 className="font-bold">Risk Trend</h2>
          <div className="mt-4 space-y-3">
            {(data.risk_trend ?? [{ date: "Q1", score: 0.65 }, { date: "Q2", score: 0.72 }]).map((p) => (
              <div key={p.date} className="flex items-center gap-3">
                <span className="w-12 font-mono text-xs text-[var(--text-muted)]">{p.date}</span>
                <div className="h-2 flex-1 rounded-full bg-[var(--bg-tertiary)]">
                  <motion.div
                    className="h-2 rounded-full bg-gradient-to-r from-[var(--violet)] to-[var(--magenta)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${p.score * 100}%` }}
                    transition={{ duration: 1 }}
                  />
                </div>
                <span className="font-mono text-xs"><CountUp end={Math.round(p.score * 100)} />%</span>
              </div>
            ))}
          </div>
        </AnimatedCard>
        <AnimatedCard delay={0.1}>
          <h2 className="font-bold">Critical Summary</h2>
          <ul className="mt-4 space-y-3">
            {(data.critical_summary ?? [{ title: "Credential exposure", severity: "critical" }]).map((f, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }} className="text-sm text-[var(--text-secondary)]">
                <span className="font-mono text-[var(--red)]">{f.severity}</span> — {f.title}
              </motion.li>
            ))}
          </ul>
        </AnimatedCard>
      </div>
    </div>
  );
}
