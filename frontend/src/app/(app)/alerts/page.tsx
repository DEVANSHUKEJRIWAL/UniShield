"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { decideHITL, fetchAlerts } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";

type Severity = "critical" | "high" | "medium" | "low";
type Alert = {
  id: string;
  title: string;
  severity: Severity;
  status: string;
  source: string;
  created_at: string;
  hitl?: boolean;
  hitl_action_id?: string;
  hitl_reasoning?: string;
};

const FILTERS: Severity[] = ["critical", "high", "medium", "low"];

export default function AlertsPage() {
  const { token, tenantId, ready } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<Severity | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchAlerts(tenantId, token)
      .then((data) =>
        setAlerts(
          data.map((a: Alert) => ({
            ...a,
            severity: a.severity as Severity,
          }))
        )
      )
      .catch(() => setAlerts([]));
  }, [ready, token, tenantId]);

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const decide = async (alert: Alert, decision: "accept" | "modify" | "reject") => {
    if (alert.hitl_action_id && token && tenantId) {
      try {
        await decideHITL(alert.hitl_action_id, tenantId, token, decision, { agent_id: alert.source });
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
    <>
      <AdminPageHeader
        title="SOC Operations"
        subtitle={`${alerts.length} open alerts · HITL review enabled`}
      />

      <div className="ac-filter-wrap">
        <button
          type="button"
          className={`ac-filter-btn${filter === "all" ? " is-active" : ""}`}
          onClick={() => setFilter("all")}
        >
          All ({alerts.length})
        </button>
        {FILTERS.map((s) => (
          <button
            key={s}
            type="button"
            className={`ac-filter-btn${filter === s ? " is-active" : ""}`}
            onClick={() => setFilter(s)}
          >
            {s} ({counts[s] ?? 0})
          </button>
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
                <div
                  className="flex items-center gap-4"
                  style={{
                    borderLeft: `4px solid var(--${alert.severity === "critical" ? "red" : alert.severity === "high" ? "amber" : "violet"})`,
                  }}
                >
                  <div className="flex-1 pl-3">
                    <p className="font-semibold">{alert.title}</p>
                    <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">
                      {alert.source} · {alert.status}
                    </p>
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
                      <TypewriterText
                        text={alert.hitl_reasoning ?? "Review recommended containment action before execution."}
                      />
                      <div className="mt-4 flex gap-3">
                        {(["accept", "modify", "reject"] as const).map((action) => (
                          <button
                            key={action}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              decide(alert, action);
                            }}
                            className="btn-accent"
                            style={{
                              background:
                                action === "accept"
                                  ? "var(--green)"
                                  : action === "modify"
                                    ? "var(--amber)"
                                    : "var(--red)",
                            }}
                          >
                            {action}
                          </button>
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
    </>
  );
}
