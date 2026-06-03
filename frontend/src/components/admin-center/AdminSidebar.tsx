"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import type { AgentRow } from "@/hooks/useAdminDashboard";
import {
  LayoutGrid,
  Radar,
  Bot,
  Globe,
  Cloud,
  FileCheck,
  AlertTriangle,
  ChevronLeft,
  HelpCircle,
  Settings,
  FileText,
  Rocket,
  BarChart3,
  Users,
  Workflow,
  GitBranch,
} from "lucide-react";
import { features } from "@/lib/features";
import type { LucideIcon } from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  countKey?: "alerts" | "agents" | "hitl";
  roles?: string[];
};

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Admin Center", icon: LayoutGrid },
  { href: "/alerts", label: "SOC Operations", icon: Radar, countKey: "alerts" },
  ...(features.orchestratorUi
    ? [
        { href: "/workflows", label: "Security Workflows", icon: Workflow } as NavItem,
        { href: "/repos", label: "Connected Repos", icon: GitBranch } as NavItem,
      ]
    : []),
  { href: "/agents", label: "AI Agents", icon: Bot, countKey: "agents" },
  { href: "/network", label: "Network", icon: Globe },
  { href: "/cloud", label: "Cloud Security", icon: Cloud },
  { href: "/compliance", label: "Compliance", icon: FileCheck },
  { href: "/investigation", label: "Incident Response", icon: AlertTriangle, countKey: "hitl" },
];

const FOOT_NAV: NavItem[] = [
  { href: "/dashboard/executive", label: "Executive", icon: BarChart3, roles: ["CISO", "READONLY_BOARD", "PLATFORM_ADMIN", "CLIENT_ADMIN"] },
  { href: "/reporting", label: "Reporting", icon: FileText, roles: ["GRC", "CISO", "READONLY_BOARD", "PLATFORM_ADMIN"] },
  { href: "/deployment", label: "Deploy", icon: Rocket, roles: ["PLATFORM_ADMIN", "SOC_ANALYST", "CISO"] },
  { href: "/clients", label: "Clients", icon: Users, roles: ["PLATFORM_ADMIN"] },
];

function formatAgentName(name: string) {
  return name.replace(/-agent$/, "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isActive(pathname: string, href: string) {
  if (href === "/dashboard") {
    return pathname === "/dashboard";
  }
  if (href === "/dashboard/executive") {
    return pathname.startsWith("/dashboard/executive");
  }
  return pathname === href || pathname.startsWith(href + "/");
}

type Props = {
  expanded: boolean;
  onToggle: () => void;
  agents: AgentRow[];
  agentsActive: number;
  agentsTotal: number;
  openAlertCount: number;
  hitlCount: number;
};

export function AdminSidebar({
  expanded,
  onToggle,
  agents,
  agentsActive,
  agentsTotal,
  openAlertCount,
  hitlCount,
}: Props) {
  const pathname = usePathname();
  const { email, role } = useAuth();
  const initials = email?.slice(0, 2).toUpperCase() ?? "US";
  const displayName = email?.split("@")[0]?.replace(/[._]/g, " ") ?? "Operator";
  const roleLabel = role?.replace(/_/g, " ") ?? "Security Administrator";

  const counts: Record<string, number> = {
    alerts: openAlertCount,
    agents: agents.length || agentsTotal,
    hitl: hitlCount,
  };

  const visibleFoot = FOOT_NAV.filter(
    (item) => !item.roles || item.roles.includes("*") || (role && item.roles.includes(role))
  );

  const liveAgents = agents.length ? agents.slice(0, 5) : [{ name: "orchestrator", status: "running" as const }];
  const warnCount = liveAgents.filter((a) => a.status !== "running").length;

  const renderNavLink = (item: NavItem) => {
    const Icon = item.icon;
    const active = isActive(pathname, item.href);
    const badge = item.countKey ? counts[item.countKey] : undefined;
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`nav-icon${active ? " active" : ""}`}
        title={item.label}
      >
        <span className="nav-icon-wrap">
          <Icon className="icon" style={{ width: 16, height: 16 }} />
        </span>
        <span className="nav-label">{item.label}</span>
        {badge != null && badge > 0 && (
          <span
            className="nav-count"
            style={{
              background:
                item.href === "/alerts" || item.href === "/investigation"
                  ? "var(--r-sec2)"
                  : "var(--purple-mid)",
            }}
          >
            {badge > 99 ? "99+" : badge}
          </span>
        )}
      </Link>
    );
  };

  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar-head">
        <div className="sidebar-logo" title="UniShield">
          <svg className="icon" style={{ width: 18, height: 18 }} viewBox="0 0 24 24">
            <path d="M12 2l8 4v6c0 5-3.5 9.5-8 10-4.5-.5-8-5-8-10V6l8-4z" />
          </svg>
        </div>
        <span className="sidebar-brand">UniShield</span>
        <button
          type="button"
          className="sidebar-toggle"
          onClick={onToggle}
          aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
          aria-expanded={expanded}
        >
          <ChevronLeft
            className="icon"
            style={{
              width: 16,
              height: 16,
              transform: expanded ? "rotate(0deg)" : "rotate(180deg)",
              transition: "transform 0.35s ease",
            }}
          />
        </button>
      </div>

      <div className="sidebar-profile">
        <div className="sidebar-profile-avatar" aria-hidden="true">
          {initials}
        </div>
        <div className="sidebar-profile-info">
          <span className="sidebar-profile-name">{displayName}</span>
          <span className="sidebar-profile-role">{roleLabel}</span>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Modules">
        {NAV.map(renderNavLink)}
      </nav>

      <div className="agent-rail" aria-label="AI agent status">
        <div className="agent-rail-compact" title={`${agentsActive} of ${agentsTotal || liveAgents.length} agents live`}>
          <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: "var(--sidebar-text)" }}>
            {agentsActive}/{agentsTotal || liveAgents.length}
          </span>
        </div>
        <div className="agent-rail-detail">
          <div className="agent-rail-panel">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span className="agent-rail-title">AI Agents</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--m3)", fontWeight: 600 }}>
                {agentsActive} live
              </span>
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {liveAgents.map((a) => (
                <li key={a.name} className="agent-row">
                  <span className={`agent-dot ${a.status === "running" || a.status === "listening" ? "is-ok" : "is-warn"}`} />
                  <span className="agent-name">{formatAgentName(a.name)}</span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: a.status === "running" || a.status === "listening" ? "var(--m3)" : "var(--r-sec1)",
                    }}
                  >
                    {a.status === "running" ? "LIVE" : a.status === "listening" ? "LIVE" : a.status === "error" ? "DEG" : "IDLE"}
                  </span>
                </li>
              ))}
            </ul>
            {warnCount > 0 && (
              <p className="mono" style={{ fontSize: 10, color: "var(--sidebar-text)", marginTop: 4 }}>
                {warnCount} degraded
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="sidebar-foot">
        {visibleFoot.map(renderNavLink)}
        <Link href="/settings" className={`nav-icon sidebar-foot-link${pathname === "/settings" ? " active" : ""}`}>
          <Settings className="icon" style={{ width: 16, height: 16 }} />
          <span className="nav-label">Settings</span>
        </Link>
        <button type="button" className="nav-icon sidebar-foot-link" style={{ border: "none", cursor: "pointer" }}>
          <HelpCircle className="icon" style={{ width: 16, height: 16 }} />
          <span className="nav-label">Support</span>
        </button>
      </div>
    </aside>
  );
}
