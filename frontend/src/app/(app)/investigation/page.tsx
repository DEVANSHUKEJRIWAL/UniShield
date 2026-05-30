"use client";

import { motion } from "framer-motion";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { RiskGauge } from "@/components/ui/RiskGauge";

const STAGES = ["Initial Access", "Execution", "Persistence", "Privilege Escalation", "Lateral Movement", "Exfiltration"];
const IOCS = [
  { type: "IP", value: "192.168.1.45", malicious: true },
  { type: "Domain", value: "evil-c2.example.com", malicious: true },
  { type: "Hash", value: "a1b2c3d4e5f6...", malicious: false },
];

export default function InvestigationPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Case Investigation</GradientText></h1>

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
            <motion.div
              key={s}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="relative z-10 flex flex-col items-center"
            >
              <div
                className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold"
                style={{
                  background: i < 4 ? "var(--violet)" : "var(--bg-surface)",
                  border: `2px solid ${i < 4 ? "var(--violet-light)" : "var(--border-default)"}`,
                  boxShadow: i === 3 ? "0 0 16px var(--red)" : undefined,
                }}
              >
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
          {["dark-web-agent", "forensics-agent", "siem-analysis-agent"].map((agent, i) => (
            <motion.div
              key={agent}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="mb-3 rounded-xl border border-[var(--border-subtle)] p-3"
            >
              <p className="font-mono text-xs text-[var(--violet-light)]">{agent}</p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
                <motion.div
                  className="h-full rounded-full bg-[var(--violet)]"
                  initial={{ width: 0 }}
                  animate={{ width: `${85 - i * 10}%` }}
                  transition={{ duration: 1, delay: 0.5 + i * 0.2 }}
                />
              </div>
            </motion.div>
          ))}
          <TypewriterText text="Credential dump correlates with T1078 Valid Accounts technique. Confidence: 0.92" />
        </AnimatedCard>

        <AnimatedCard delay={0.3} className="lg:col-span-2">
          <h3 className="mb-4 font-bold">Extracted IOCs</h3>
          <div className="space-y-2">
            {IOCS.map((ioc, i) => (
              <motion.div
                key={ioc.value}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-center justify-between rounded-lg bg-[var(--bg-tertiary)] p-3 font-mono text-xs"
              >
                <span className="text-[var(--text-muted)]">{ioc.type}</span>
                <span>{ioc.value}</span>
                {ioc.malicious && (
                  <motion.span
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className="text-[var(--red)]"
                  >
                    MALICIOUS
                  </motion.span>
                )}
              </motion.div>
            ))}
          </div>
          <div className="mt-6 flex justify-center">
            <RiskGauge score={88} size="md" label="Case Risk" />
          </div>
        </AnimatedCard>
      </div>
    </div>
  );
}
