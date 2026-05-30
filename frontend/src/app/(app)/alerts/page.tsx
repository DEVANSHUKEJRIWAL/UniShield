"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { decideHITL, fetchAlerts, fetchHITLQueue } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { GradientText } from "@/components/ui/primitives";

type Severity = "critical" | "high" | "medium" | "low";
type Alert = { id: string; title: string; severity: Severity; status: string; source: string; created_at: string; hitl?: boolean; hitlActionId?: string };

const FILTERS: Severity[] = ["critical", "high", "medium", "low"];

export default function AlertsPage() {
  const { token, tenantId } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<Severity | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [hitlByFinding, setHitlByFinding] = useState<Record<string, { action_id?: string; reasoning?: string }>>({});

  useEffect(() => {
    if (!token || !tenantId) return;
    Promise.all([fetchAlerts(tenantId, token), fetchHITLQueue(tenantId, token)])
      .then(([alertData, hitlQueue]) => {
        const hitlMap: Record<string, { action_id?: string; reasoning?: string }> = {};
        (hitlQueue as Array<{ action_id?: string; action?: { finding_id?: string }; reasoning?: string }>).forEach((item) => {
          const fid = item.action?.finding_id;
          if (fid) hitlMap[fid] = { action_id: item.action_id, reasoning: item.reasoning };
        });
        setHitlByFinding(hitlMap);
        setAlerts(
          alertData.map((a: Alert & { finding_id?: string }) => ({
            ...a,
            severity: a.severity as Severity,
            hitl: Boolean(a.finding_id && hitlMap[a.finding_id ?? ""]),
            hitlActionId: a.finding_id ? hitlMap[a.finding_id]?.action_id : undefined,
          }))
        );
      })
      .catch(() => setAlerts([]));
  }, [token, tenantId]);

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const decide = async (alert: Alert, decision: "accept" | "modify" | "reject") => {
    if (alert.hitlActionId && token && tenantId) {
      try {
        await decideHITL(alert.hitlActionId, tenantId, token, decision, { agent_id: alert.source });
      } catch {
        toast.error("HITL decision failed");
        return;
      }
    }
    toast.success(`Action ${decision}`, { description: "Decision recorded" });
    setExpanded(null);
    setAlerts((prev) => prev.map((a) => (a.id === alert.id ? { ...a, hitl: false } : a)));
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
                      <TypewriterText text={hitlByFinding[alert.id]?.reasoning ?? "Review recommended containment action before execution."} />
                      <div className="mt-4 flex gap-3">
                        {(["accept", "modify", "reject"] as const).map((action) => (
                          <motion.button
                            key={action}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.92 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              decide(alert, action);
                            }}
                            className="rounded-xl px-4 py-2 text-xs font-bold uppercase text-white"
                            style={{
                              background: action === "accept" ? "var(--green)" : action === "modify" ? "var(--amber)" : "var(--red)",
                            }}
                          >
                            {action}
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
