"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchWorkflowMetrics } from "@/lib/workflows-api";
import { features } from "@/lib/features";
import { AdminCenterShell } from "./admin-center/AdminCenterShell";
import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Toaster } from "sonner";
import type { AgentRow } from "@/hooks/useAdminDashboard";

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

const pageTransition = {
  type: "tween" as const,
  ease: [0.4, 0, 0.2, 1] as [number, number, number, number],
  duration: 0.22,
};

function normalizeAgentStatus(status: string): AgentRow["status"] {
  if (status === "running") return "running";
  if (status === "listening") return "listening";
  if (status === "error") return "error";
  return "idle";
}

function applyAgentMetrics(
  metrics: Awaited<ReturnType<typeof fetchWorkflowMetrics>>,
  setAgents: (rows: AgentRow[]) => void,
  setAgentsActive: (n: number) => void,
  setAgentsTotal: (n: number) => void,
  setHitlCount: (n: number) => void,
  setOpenAlertCount: (n: number) => void,
) {
  if (!metrics.available) return false;
  setHitlCount(metrics.kpis?.hitl_queue ?? metrics.paused_workflows ?? 0);
  setOpenAlertCount(metrics.kpis?.active_alerts ?? metrics.priority_queue?.length ?? 0);
  const rows = (metrics.agents ?? []).map((a) => ({
    name: a.name,
    status: normalizeAgentStatus(a.status),
  }));
  setAgents(rows);
  setAgentsActive(
    metrics.agents_active ??
      rows.filter((a) => a.status === "running" || a.status === "listening").length
  );
  setAgentsTotal(metrics.agents_total ?? rows.length);
  return true;
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { token, tenantId } = useAuth();
  const [hitlCount, setHitlCount] = useState(0);
  const [openAlertCount, setOpenAlertCount] = useState(0);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [agentsActive, setAgentsActive] = useState(0);
  const [agentsTotal, setAgentsTotal] = useState(0);

  useEffect(() => {
    if (!token || !tenantId || !features.orchestratorUi) return;

    fetchWorkflowMetrics(tenantId, token)
      .then((metrics) => {
        applyAgentMetrics(
          metrics,
          setAgents,
          setAgentsActive,
          setAgentsTotal,
          setHitlCount,
          setOpenAlertCount,
        );
      })
      .catch(() => {});
  }, [token, tenantId, pathname]);

  useEffect(() => {
    if (!token || !tenantId || !features.orchestratorUi) return;

    const poll = window.setInterval(() => {
      fetchWorkflowMetrics(tenantId, token)
        .then((metrics) => {
          applyAgentMetrics(
            metrics,
            setAgents,
            setAgentsActive,
            setAgentsTotal,
            setHitlCount,
            setOpenAlertCount,
          );
        })
        .catch(() => {});
    }, 30000);

    return () => window.clearInterval(poll);
  }, [token, tenantId]);

  return (
    <>
      <AdminCenterShell
        hitlCount={hitlCount}
        openAlertCount={openAlertCount}
        agents={agents}
        agentsActive={agentsActive}
        agentsTotal={agentsTotal}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={pathname}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="ac-page"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </AdminCenterShell>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--surface-card)",
            border: "1px solid var(--border-dim)",
            color: "var(--text-primary)",
          },
        }}
      />
    </>
  );
}
