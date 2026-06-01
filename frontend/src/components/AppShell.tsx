"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchAgentHealth, fetchHITLQueue } from "@/lib/api";
import { Navbar } from "./Navbar";
import { ParticleBackground } from "./ParticleBackground";
import { AdminCenterShell } from "./admin-center/AdminCenterShell";
import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Toaster } from "sonner";
import type { AgentRow } from "@/hooks/useAdminDashboard";

const pageVariants = {
  initial: { opacity: 0, x: 20, filter: "blur(4px)" },
  animate: { opacity: 1, x: 0, filter: "blur(0px)" },
  exit: { opacity: 0, x: -20, filter: "blur(4px)" },
};

const pageTransition = {
  type: "tween" as const,
  ease: [0.4, 0, 0.2, 1] as [number, number, number, number],
  duration: 0.25,
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { token, tenantId } = useAuth();
  const [hitlCount, setHitlCount] = useState(0);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [agentsActive, setAgentsActive] = useState(0);
  const [agentsTotal, setAgentsTotal] = useState(0);
  const isAdminCenter = pathname === "/dashboard";

  useEffect(() => {
    if (!token || !tenantId) return;
    fetchHITLQueue(tenantId, token)
      .then((q) => setHitlCount(Array.isArray(q) ? q.length : 0))
      .catch(() => setHitlCount(0));
  }, [token, tenantId, pathname]);

  useEffect(() => {
    if (!isAdminCenter || !token || !tenantId) return;
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
  }, [isAdminCenter, token, tenantId]);

  if (isAdminCenter) {
    return (
      <>
        <AdminCenterShell
          hitlCount={hitlCount}
          agents={agents}
          agentsActive={agentsActive}
          agentsTotal={agentsTotal}
        >
          {children}
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

  return (
    <>
      <ParticleBackground />
      <Navbar hitlCount={hitlCount} />
      <AnimatePresence mode="wait">
        <motion.div key={pathname} className="relative z-10 min-h-screen pt-16">
          <motion.div
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            exit={{ scaleX: 0, originX: 1 }}
            transition={{ duration: 0.25 }}
            className="fixed left-0 right-0 top-16 z-50 h-0.5 bg-gradient-to-r from-[var(--violet)] to-[var(--magenta)]"
          />
          <motion.main
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="px-6 pb-12 pt-6"
          >
            {children}
          </motion.main>
        </motion.div>
      </AnimatePresence>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            color: "var(--text-primary)",
          },
        }}
      />
    </>
  );
}
