"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  fetchDashboard,
  fetchAlerts,
  fetchAgentHealth,
  fetchExecutiveDashboard,
  fetchHITLQueue,
  fetchAiBrief,
  agentWsUrl,
} from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

export type AlertEvent = {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  message: string;
  time: string;
  source: string;
  bfsi?: boolean;
  findingId?: string | null;
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
  lat?: number;
  lng?: number;
  code?: string;
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

export type KpiSparklines = {
  risk: number[];
  critical: number[];
  findings: number[];
  agents: number[];
  compliance: number[];
  hitl: number[];
};

export type AiBriefData = {
  headline: string;
  tabs: { exec: string; soc: string; compliance: string };
};

const TREND_FALLBACK: TrendPoint[] = [
  { label: "W1", score: 45 },
  { label: "W2", score: 52 },
  { label: "W3", score: 48 },
  { label: "W4", score: 61 },
  { label: "W5", score: 58 },
  { label: "W6", score: 72 },
];

const SPARK_FALLBACK: KpiSparklines = {
  risk: [65, 68, 70, 72, 71, 72],
  critical: [1, 2, 2, 3, 2, 2],
  findings: [4, 5, 6, 8, 7, 8],
  agents: [40, 55, 60, 70, 65, 72],
  compliance: [80, 81, 82, 83, 82, 84],
  hitl: [0, 1, 1, 2, 1, 1],
};

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

function mapPriorityItem(
  item: {
    id: string;
    severity: string;
    title: string;
    source: string;
    time: string;
    bfsi?: boolean;
    finding_id?: string | null;
  }
): AlertEvent {
  return {
    id: item.id,
    severity: item.severity as AlertEvent["severity"],
    message: item.title,
    time: new Date(item.time).toLocaleTimeString(),
    source: item.source,
    bfsi: item.bfsi,
    findingId: item.finding_id,
  };
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
  const [sparklines, setSparklines] = useState<KpiSparklines>(SPARK_FALLBACK);
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [criticalSummary, setCriticalSummary] = useState<Array<{ title: string; severity: string }>>([]);
  const [vendorRisks, setVendorRisks] = useState<VendorRiskRow[]>([]);
  const [threatOrigins, setThreatOrigins] = useState<ThreatOriginRow[]>([]);
  const [aiBrief, setAiBrief] = useState<AiBriefData | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const eventKeyRef = useRef(0);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

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
        if (d.kpi_sparklines) setSparklines({ ...SPARK_FALLBACK, ...d.kpi_sparklines });
        if (Array.isArray(d.priority_queue) && d.priority_queue.length) {
          setAlerts(d.priority_queue.map(mapPriorityItem));
        }
        setUpdatedAt(new Date());
      })
      .catch(() => {});

    fetchAlerts(tenantId, token)
      .then((items) => {
        if (items.length === 0) return;
        const mapped = items
          .map(
            (a: {
              id: string;
              severity: string;
              title: string;
              source: string;
              created_at: string;
              finding_id?: string;
            }) => ({
              id: a.id,
              severity: a.severity as AlertEvent["severity"],
              message: a.title,
              time: new Date(a.created_at).toLocaleTimeString(),
              source: a.source,
              findingId: a.finding_id,
              bfsi: /dark-web|insider|source-code|bfsi/i.test(`${a.source} ${a.title}`),
            })
          )
          .sort((a: AlertEvent, b: AlertEvent) => severityRank(a.severity) - severityRank(b.severity));
        setAlerts((prev) => (prev.length ? prev : mapped.slice(0, 12)));
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

    fetchAiBrief(tenantId, token, range)
      .then((d) => {
        if (d.tabs) {
          setAiBrief({ headline: d.headline ?? "", tabs: d.tabs });
        }
      })
      .catch(() => {});
  }, [ready, token, tenantId, range, refreshKey]);

  const displayName = email?.split("@")[0]?.replace(/[._]/g, " ") ?? "Operator";
  const initials = email?.slice(0, 2).toUpperCase() ?? "US";

  return {
    kpis,
    trend,
    sparklines,
    alerts,
    agents,
    criticalSummary,
    vendorRisks,
    threatOrigins,
    aiBrief,
    updatedAt,
    displayName,
    initials,
    tenantId,
    refresh,
  };
}
