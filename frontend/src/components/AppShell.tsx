"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchAgentHealth, fetchAlerts, fetchHITLQueue } from "@/lib/api";
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

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { token, tenantId } = useAuth();
  const [hitlCount, setHitlCount] = useState(0);
  const [openAlertCount, setOpenAlertCount] = useState(0);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [agentsActive, setAgentsActive] = useState(0);
  const [agentsTotal, setAgentsTotal] = useState(0);

  useEffect(() => {
    if (!token || !tenantId) return;
    fetchHITLQueue(tenantId, token)
      .then((q) => setHitlCount(Array.isArray(q) ? q.length : 0))
      .catch(() => setHitlCount(0));
    fetchAlerts(tenantId, token)
      .then((items) => setOpenAlertCount(Array.isArray(items) ? items.length : 0))
      .catch(() => setOpenAlertCount(0));
  }, [token, tenantId, pathname]);

  useEffect(() => {
    if (!token || !tenantId) return;
    fetchAgentHealth(tenantId, token)
      .then((d) => {
        const rows = (d.agents ?? []).map((a: { name: string; status: string }) => ({
          name: a.name,
          status: (a.status === "running" ? "running" : a.status === "error" ? "error" : "idle") as AgentRow["status"],
        }));
        setAgents(rows);
        setAgentsActive(rows.filter((a: AgentRow) => a.status === "running").length);
        setAgentsTotal(rows.length);
      })
      .catch(() => {});
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
