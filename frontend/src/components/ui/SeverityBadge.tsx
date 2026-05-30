"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Severity = "critical" | "high" | "medium" | "low" | "info";

const COLORS: Record<Severity, { bg: string; text: string; border: string }> = {
  critical: { bg: "var(--red-dim)", text: "var(--red)", border: "rgba(244,63,94,0.4)" },
  high: { bg: "var(--amber-dim)", text: "var(--amber)", border: "rgba(245,158,11,0.4)" },
  medium: { bg: "var(--magenta-dim)", text: "var(--magenta)", border: "rgba(192,38,168,0.3)" },
  low: { bg: "var(--blue-dim)", text: "var(--blue)", border: "rgba(59,130,246,0.3)" },
  info: { bg: "var(--violet-dim)", text: "var(--text-muted)", border: "var(--border-default)" },
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  const c = COLORS[severity];
  return (
    <motion.span
      animate={severity === "critical" ? { scale: [1, 1.05, 1] } : {}}
      transition={{ repeat: severity === "critical" ? Infinity : 0, duration: 1.5 }}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider font-mono",
        className
      )}
      style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
    >
      {severity}
    </motion.span>
  );
}
