"use client";

import CountUp from "react-countup";
import { motion } from "framer-motion";

interface RiskGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  label?: string;
}

export function RiskGauge({ score, size = "md", label }: RiskGaugeProps) {
  const clamped = Math.min(100, Math.max(0, score));
  const color = clamped > 60 ? "var(--red)" : clamped > 30 ? "var(--amber)" : "var(--green)";
  const dim = size === "lg" ? 120 : size === "md" ? 80 : 48;
  const stroke = size === "lg" ? 8 : 6;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (clamped / 100) * circ;

  return (
    <div className="relative inline-flex flex-col items-center">
      <svg width={dim} height={dim} className="-rotate-90">
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="var(--border-default)" strokeWidth={stroke} />
        <motion.circle
          cx={dim / 2}
          cy={dim / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className={size === "lg" ? "text-3xl font-extrabold" : size === "md" ? "text-xl font-bold" : "text-sm font-bold"}>
          <CountUp end={clamped} duration={1.5} />
        </span>
        {label && <span className="text-[9px] uppercase tracking-widest text-[var(--text-muted)] font-mono">{label}</span>}
      </div>
    </div>
  );
}
