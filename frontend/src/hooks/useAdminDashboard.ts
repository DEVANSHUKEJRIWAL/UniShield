"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  fetchDashboard,
  fetchAlerts,
  fetchAgentHealth,
  fetchExecutiveDashboard,
  fetchHITLQueue,
  agentWsUrl,
} from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

export type AlertEvent = {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  message: string;
  time: string;
  source: string;
};

export type AgentRow = {
  name: string;
  status: "running" | "listening" | "idle" | "error";
};

export type VendorRiskRow = {
  name: string;
  score: number;
  issue: string;
  severity?: string;
};

export type ThreatOriginRow = {
  region: string;
  count: number;
  severity: string;
  source?: string;
};

export type DashboardRange = "24h" | "7d" | "30d";

export type DashboardKpis = {
  riskScore: number;
  riskLabel: string;
  activeAlerts: number;
  totalFindings: number;
  criticalFindings: number;
  agentsActive: number;
  agentsTotal: number;
  hitlQueue: number;
  compliancePct: number | null;
};

export type TrendPoint = { label: string; score: number };

const TREND_FALLBACK: TrendPoint[] = [
  { label: "W1", score: 45 },
  { label: "W2", score: 52 },
  { label: "W3", score: 48 },
  { label: "W4", score: 61 },
  { label: "W5", score: 58 },
  { label: "W6", score: 72 },
];

function severityRank(s: string): number {
  if (s === "critical") return 0;
  if (s === "high") return 1;
  if (s === "medium") return 2;
  if (s === "low") return 3;
  return 4;
}

function normalizeAgentStatus(status: string): AgentRow["status"] {
  if (status === "running") return "running";
  if (status === "listening") return "listening";
  if (status === "error") return "error";
  return "idle";
}

function isAgentLive(status: AgentRow["status"]) {
  return status === "running" || status === "listening";
}

export function useAdminDashboard(range: DashboardRange = "7d") {
  const { token, tenantId, ready, email } = useAuth();
  const [kpis, setKpis] = useState<DashboardKpis>({
    riskScore: 72,
    riskLabel: "Elevated",
    activeAlerts: 0,
    totalFindings: 0,
    criticalFindings: 0,
    agentsActive: 0,
    agentsTotal: 0,
    hitlQueue: 0,
    compliancePct: null,
  });
  const [trend, setTrend] = useState<TrendPoint[]>(TREND_FALLBACK);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [criticalSummary, setCriticalSummary] = useState<Array<{ title: string; severity: string }>>([]);
  const [vendorRisks, setVendorRisks] = useState<VendorRiskRow[]>([]);
  const [threatOrigins, setThreatOrigins] = useState<ThreatOriginRow[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const eventKeyRef = useRef(0);

  useWebSocket(tenantId ? agentWsUrl(tenantId) : null, {
    onMessage: (data) => {
      const msg = data as {
        agent?: string;
        finding?: { finding_id?: string; title?: string; severity?: string };
      };
      const finding = msg.finding;
      if (!finding?.title) return;
      eventKeyRef.current += 1;
      const findingId = finding.finding_id;
      const evt: AlertEvent = {
        id: findingId ?? `${msg.agent ?? "agent"}-${Date.now()}-${eventKeyRef.current}`,
        severity: (finding.severity ?? "medium") as AlertEvent["severity"],
        message: finding.title,
        time: new Date().toLocaleTimeString(),
        source: msg.agent ?? "agent",
      };
      setAlerts((prev) => [evt, ...prev].slice(0, 12));
    },
  });

  useEffect(() => {
    if (!ready || !token || !tenantId) return;

    fetchDashboard(tenantId, token, range)
      .then((d) => {
        const score = Math.round((d.kpis?.risk_score ?? 0.72) * 100);
        setKpis((prev) => ({
          ...prev,
          riskScore: score,
          riskLabel: d.kpis?.risk_label ?? "Elevated",
          activeAlerts: d.kpis?.active_alerts ?? 0,
          totalFindings: d.kpis?.total_findings ?? 0,
          criticalFindings: d.kpis?.critical_findings ?? 0,
          agentsActive: d.agents_active ?? 0,
          agentsTotal: d.agents_total ?? 0,
          hitlQueue: d.hitl_queue_depth ?? 0,
        }));
        if (d.risk_trend?.length) {
          setTrend(
            d.risk_trend.map((p: { label: string; score: number }) => ({
              label: p.label,
              score: p.score,
            }))
          );
        }
        if (Array.isArray(d.vendor_risks)) setVendorRisks(d.vendor_risks);
        if (Array.isArray(d.threat_origins)) setThreatOrigins(d.threat_origins);
        setUpdatedAt(new Date());
      })
      .catch(() => {});

    fetchAlerts(tenantId, token)
      .then((items) => {
        const mapped = items
          .map(
            (a: { id: string; severity: string; title: string; source: string; created_at: string }) => ({
              id: a.id,
              severity: a.severity as AlertEvent["severity"],
              message: a.title,
              time: new Date(a.created_at).toLocaleTimeString(),
              source: a.source,
            })
          )
          .sort((a: AlertEvent, b: AlertEvent) => severityRank(a.severity) - severityRank(b.severity));
        setAlerts(mapped.slice(0, 12));
      })
      .catch(() => {});

    fetchAgentHealth(tenantId, token)
      .then((d) => {
        const rows = (d.agents ?? []).map((a: { name: string; status: string }) => ({
          name: a.name,
          status: normalizeAgentStatus(a.status),
        }));
        setAgents(rows);
        setKpis((prev) => ({
          ...prev,
          agentsActive: rows.filter((a: AgentRow) => isAgentLive(a.status)).length,
          agentsTotal: rows.length || prev.agentsTotal,
        }));
      })
      .catch(() => {});

    fetchExecutiveDashboard(tenantId, token)
      .then((d) => {
        const cs = d.compliance_status as Record<string, number> | undefined;
        if (cs) {
          const vals = Object.values(cs);
          const avg = vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100) : null;
          setKpis((prev) => ({ ...prev, compliancePct: avg }));
        }
        if (d.critical_summary?.length) {
          setCriticalSummary(d.critical_summary);
        }
      })
      .catch(() => {});

    fetchHITLQueue(tenantId, token)
      .then((q) => {
        const depth = Array.isArray(q) ? q.length : 0;
        setKpis((prev) => ({ ...prev, hitlQueue: depth }));
      })
      .catch(() => {});
  }, [ready, token, tenantId, range]);

  const displayName = email?.split("@")[0]?.replace(/[._]/g, " ") ?? "Operator";
  const initials = email?.slice(0, 2).toUpperCase() ?? "US";

  return {
    kpis,
    trend,
    alerts,
    agents,
    criticalSummary,
    vendorRisks,
    threatOrigins,
    updatedAt,
    displayName,
    initials,
    tenantId,
  };
}
