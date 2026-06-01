"use client";

import { ReactNode, useEffect, useState } from "react";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopnav } from "./AdminTopnav";
import type { AgentRow } from "@/hooks/useAdminDashboard";

type AdminCenterShellProps = {
  children: ReactNode;
  hitlCount?: number;
  agents?: AgentRow[];
  agentsActive?: number;
  agentsTotal?: number;
};

export function AdminCenterShell({
  children,
  hitlCount = 0,
  agents = [],
  agentsActive = 0,
  agentsTotal = 0,
}: AdminCenterShellProps) {
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("unishield-sidebar");
    if (stored === "collapsed") setExpanded(false);
  }, []);

  const toggleSidebar = () => {
    const next = !expanded;
    setExpanded(next);
    localStorage.setItem("unishield-sidebar", next ? "expanded" : "collapsed");
  };

  return (
    <div className={`admin-center${expanded ? " sidebar-expanded" : ""}`}>
      <AdminSidebar
        expanded={expanded}
        onToggle={toggleSidebar}
        agents={agents}
        agentsActive={agentsActive}
        agentsTotal={agentsTotal}
        alertCount={hitlCount}
      />
      <AdminTopnav hitlCount={hitlCount} />
      <main className="main-wrap">{children}</main>
    </div>
  );
}
