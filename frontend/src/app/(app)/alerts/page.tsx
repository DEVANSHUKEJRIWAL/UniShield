"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { fetchAlerts } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { GradientText } from "@/components/ui/primitives";

type Severity = "critical" | "high" | "medium" | "low";
type Alert = { id: string; title: string; severity: Severity; status: string; source: string; created_at: string; hitl?: boolean };

const FILTERS: Severity[] = ["critical", "high", "medium", "low"];

export default function AlertsPage() {
  const { token, tenantId } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<Severity | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (token && tenantId) {
      fetchAlerts(tenantId, token).then((data) =>
        setAlerts(
          data.map((a: Alert, i: number) => ({
            ...a,
            severity: a.severity as Severity,
            hitl: i === 0,
          }))
        )
      ).catch(() =>
        setAlerts([
          { id: "1", title: "Credential exposure on dark web", severity: "critical", status: "open", source: "dark-web-agent", created_at: new Date().toISOString(), hitl: true },
          { id: "2", title: "Anomalous privileged login", severity: "high", status: "open", source: "insider-threat-agent", created_at: new Date().toISOString() },
        ])
      );
    }
  }, [token, tenantId]);

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const decide = (id: string, decision: string) => {
    toast.success(`Action ${decision}`, { description: "Containment workflow initiated" });
    setExpanded(null);
    setAlerts((prev) => prev.filter((a) => a.id !== id || !a.hitl));
  };

  const counts = FILTERS.reduce(
    (acc, s) => ({ ...acc, [s]: alerts.filter((a) => a.severity === s).length }),
    {} as Record<Severity, number>
  );

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Alert Command Center</GradientText></h1>

      <div className="relative flex gap-2">
        {FILTERS.map((s) => (
          <motion.button
            key={s}
            onClick={() => setFilter(s)}
            whileTap={{ scale: 0.95 }}
            className="relative rounded-full px-4 py-2 text-xs font-bold uppercase font-mono"
            style={{ color: filter === s ? "var(--text-primary)" : "var(--text-secondary)" }}
          >
            {filter === s && (
              <motion.div
                layoutId="alert-filter"
                className="absolute inset-0 rounded-full"
                style={{ background: "var(--violet-dim)", border: "1px solid rgba(124,58,237,0.3)" }}
              />
            )}
            <span className="relative z-10">{s} ({counts[s] ?? 0})</span>
          </motion.button>
        ))}
      </div>

      <div className="space-y-3">
        <AnimatePresence>
          {filtered.map((alert, i) => (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ delay: i * 0.05 }}
            >
              <AnimatedCard
                className="cursor-pointer"
                onClick={() => setExpanded(expanded === alert.id ? null : alert.id)}
              >
                <div className="flex items-center gap-4" style={{ borderLeft: `4px solid var(--${alert.severity === "critical" ? "red" : alert.severity === "high" ? "amber" : "violet"})` }}>
                  <div className="flex-1 pl-3">
                    <p className="font-semibold">{alert.title}</p>
                    <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">{alert.source} · {alert.status}</p>
                  </div>
                  <SeverityBadge severity={alert.severity} />
                </div>

                <AnimatePresence>
                  {expanded === alert.id && alert.hitl && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="mt-4 overflow-hidden border-t border-[var(--border-subtle)] pt-4"
                    >
                      <TypewriterText text="Recommend isolating workstation-42 due to lateral movement indicators from SIEM correlation." />
                      <div className="mt-4 flex gap-3">
                        {[
                          { label: "✓ ACCEPT", color: "var(--green)", action: "accepted" },
                          { label: "✎ MODIFY", color: "var(--amber)", action: "modified" },
                          { label: "✗ REJECT", color: "var(--red)", action: "rejected" },
                        ].map((btn) => (
                          <motion.button
                            key={btn.action}
                            whileHover={{ scale: 1.05, boxShadow: `0 0 20px ${btn.color}` }}
                            whileTap={{ scale: 0.92 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              decide(alert.id, btn.action);
                            }}
                            className="rounded-xl px-4 py-2 text-xs font-bold text-white"
                            style={{ background: btn.color }}
                          >
                            {btn.label}
                          </motion.button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </AnimatedCard>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
