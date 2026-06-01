"use client";

import { motion } from "framer-motion";

export function GradientText({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`t-title ${className}`} style={{ letterSpacing: "-0.03em" }}>
      {children}
    </span>
  );
}

export function AgentStatusDot({ status }: { status: "running" | "idle" | "error" }) {
  const colors = {
    running: { bg: "var(--green)", shadow: "0 0 8px var(--green)" },
    idle: { bg: "var(--text-muted)", shadow: "none" },
    error: { bg: "var(--red)", shadow: "0 0 8px var(--red)" },
  };
  const c = colors[status];
  return (
    <motion.div
      animate={status !== "idle" ? { scale: [1, 1.3, 1] } : {}}
      transition={{ repeat: Infinity, duration: status === "error" ? 0.8 : 1.5 }}
      className="h-2 w-2 rounded-full"
      style={{ background: c.bg, boxShadow: c.shadow }}
    />
  );
}

export function GlassPanel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-[var(--border-subtle)] backdrop-blur-xl ${className}`}
      style={{
        background: "color-mix(in srgb, var(--bg-surface) 85%, transparent)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
      }}
    >
      {children}
    </div>
  );
}
