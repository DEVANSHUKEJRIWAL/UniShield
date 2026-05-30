"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchDashboard, fetchAlerts } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { KPIStrip } from "@/components/KPIStrip";
import { ThreatFeed } from "@/components/ThreatFeed";
import { AgentStatusCard } from "@/components/AgentStatusCard";
import { HITLDecisionCard } from "@/components/HITLDecisionCard";
import { useWebSocket } from "@/hooks/useWebSocket";
import { wsUrl } from "@/lib/api";

export default function DashboardPage() {
  const { token, tenantId } = useAuth();
  const [kpis, setKpis] = useState<Array<{ label: string; value: string | number; trend?: string }>>([]);
  const [events, setEvents] = useState<Array<{ id: string; severity: "critical" | "high" | "medium" | "low" | "info"; message: string; timestamp: string; source: string }>>([]);
  const [agents, setAgents] = useState<Array<{ name: string; status: "idle" | "running" | "error"; healthy: boolean }>>([]);
  const { connected } = useWebSocket(tenantId ? wsUrl(tenantId) : null, {
    onMessage: (data) => {
      const d = data as Record<string, string>;
      setEvents((prev) => [{
        id: Date.now().toString(),
        severity: "medium" as const,
        message: JSON.stringify(d).slice(0, 120),
        timestamp: "just now",
        source: d.source_vendor ?? "stream",
      }, ...prev].slice(0, 20));
    },
  });

  useEffect(() => {
    if (!token || !tenantId) return;
    fetchDashboard(tenantId, token).then((d) => {
      setKpis([
        { label: "Active Alerts", value: d.kpis?.active_alerts ?? 0 },
        { label: "Risk Score", value: Math.round((d.kpis?.risk_score ?? 0) * 100), trend: d.kpis?.risk_label },
        { label: "Critical Findings", value: d.kpis?.critical_findings ?? 0 },
        { label: "HITL Queue", value: d.hitl_queue_depth ?? 0, trend: connected ? "Live" : "Offline" },
      ]);
    }).catch(() => {
      setKpis([
        { label: "Active Alerts", value: 23, trend: "+3 today" },
        { label: "Risk Score", value: 72, trend: "High" },
        { label: "Agents Running", value: "4/13" },
        { label: "HITL Queue", value: 2 },
      ]);
    });
    fetchAlerts(tenantId, token).then((alerts) => {
      setEvents(alerts.map((a: { id: string; severity: string; title: string; source: string; created_at: string }) => ({
        id: a.id,
        severity: a.severity as "critical" | "high" | "medium" | "low" | "info",
        message: a.title,
        timestamp: new Date(a.created_at).toLocaleString(),
        source: a.source,
      })));
    }).catch(() => {});
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/agents/status/${tenantId}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => r.json()).then((d) => {
      setAgents((d.agents ?? []).slice(0, 6).map((a: { name: string; status: string; healthy: boolean }) => ({
        name: a.name,
        status: a.status as "idle" | "running" | "error",
        healthy: a.healthy,
      })));
    }).catch(() => {
      setAgents([
        { name: "orchestrator", status: "running", healthy: true },
        { name: "dark-web-agent", status: "running", healthy: true },
        { name: "threat-intel-agent", status: "idle", healthy: true },
      ]);
    });
  }, [token, tenantId, connected]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <header className="mb-8">
          <h1 className="text-2xl font-bold">SOC Dashboard</h1>
          <p className="mt-1 text-[var(--text-secondary)]">{tenantId} — live threat monitoring</p>
        </header>
        <section className="mb-8"><KPIStrip metrics={kpis} /></section>
        <div className="mb-6">
          <HITLDecisionCard
            action={{ agent_id: "incident-response-agent", confidence: 0.88, reasoning: "Recommend isolating workstation-42 due to lateral movement indicators" }}
            onDecide={() => {}}
          />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ThreatFeed events={events.length ? events : [{ id: "1", severity: "info", message: "Connect to API and run seed-local.sh for live data", timestamp: "now", source: "system" }]} liveStream={connected} />
          </div>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Agent Status</h2>
            {agents.map((a) => <AgentStatusCard key={a.name} agent={a} />)}
          </div>
        </div>
      </main>
    </div>
  );
}
