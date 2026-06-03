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
import { fetchWorkflowMetrics, type WorkflowMetrics } from "@/lib/workflows-api";
import { features } from "@/lib/features";
import { useWebSocket } from "@/hooks/useWebSocket";

export type AlertEvent = {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  message: string;
  time: string;
  source: string;
  bfsi?: boolean;
  findingId?: string | null;
  workflowId?: string;
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

export type DashboardMetricsSource = "legacy" | "orchestrator";

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

function normalizeRiskScore(raw: number): number {
  return raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
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

function mapWorkflowPriority(item: NonNullable<WorkflowMetrics["priority_queue"]>[number]): AlertEvent {
  return {
    id: item.id,
    severity: item.severity as AlertEvent["severity"],
    message: item.title,
    time: item.time ? new Date(item.time).toLocaleTimeString() : "",
    source: item.source,
    bfsi: true,
    workflowId: item.workflow_id,
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
  const [metricsSource, setMetricsSource] = useState<DashboardMetricsSource>("legacy");
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

    let cancelled = false;

    const load = async () => {
      const orchEnabled = features.orchestratorDashboardMetrics;
      const [
        dashboardResult,
        metricsResult,
        alertsResult,
        agentHealthResult,
        executiveResult,
        hitlResult,
        aiBriefResult,
      ] = await Promise.allSettled([
        fetchDashboard(tenantId, token, range),
        orchEnabled ? fetchWorkflowMetrics(tenantId, token) : Promise.resolve(null),
        fetchAlerts(tenantId, token),
        fetchAgentHealth(tenantId, token),
        fetchExecutiveDashboard(tenantId, token),
        fetchHITLQueue(tenantId, token),
        fetchAiBrief(tenantId, token, range),
      ]);

      if (cancelled) return;

      const dashboard = dashboardResult.status === "fulfilled" ? dashboardResult.value : null;
      const metrics = metricsResult.status === "fulfilled" ? metricsResult.value : null;
      const useOrchestrator = Boolean(orchEnabled && metrics?.available);

      let nextKpis: DashboardKpis = {
        riskScore: 72,
        riskLabel: "Elevated",
        activeAlerts: 0,
        totalFindings: 0,
        criticalFindings: 0,
        agentsActive: 0,
        agentsTotal: 0,
        hitlQueue: 0,
        compliancePct: null,
      };
      let nextTrend = TREND_FALLBACK;
      let nextSparklines: KpiSparklines = SPARK_FALLBACK;
      let nextAlerts: AlertEvent[] = [];
      let nextAgents: AgentRow[] = [];

      if (useOrchestrator && metrics?.kpis) {
        nextKpis = {
          ...nextKpis,
          riskScore: normalizeRiskScore(metrics.kpis.risk_score),
          riskLabel: metrics.kpis.risk_label ?? nextKpis.riskLabel,
          totalFindings: metrics.kpis.total_findings ?? 0,
          criticalFindings: metrics.kpis.critical_findings ?? 0,
          activeAlerts: metrics.kpis.active_alerts ?? 0,
          agentsActive: metrics.agents_active ?? 0,
          agentsTotal: metrics.agents_total ?? 0,
        };
        if (metrics.risk_trend?.length) {
          nextTrend = metrics.risk_trend.map((p) => ({ label: p.label, score: p.score }));
        }
        if (metrics.kpi_sparklines) {
          nextSparklines = { ...SPARK_FALLBACK, ...metrics.kpi_sparklines };
        }
        if (metrics.priority_queue?.length) {
          nextAlerts = metrics.priority_queue.map(mapWorkflowPriority);
        }
        if (metrics.agents?.length) {
          nextAgents = metrics.agents.map((a) => ({
            name: a.name,
            status: normalizeAgentStatus(a.status),
          }));
        }
      } else if (dashboard) {
        const score = Math.round((dashboard.kpis?.risk_score ?? 0.72) * 100);
        nextKpis = {
          ...nextKpis,
          riskScore: score,
          riskLabel: dashboard.kpis?.risk_label ?? "Elevated",
          activeAlerts: dashboard.kpis?.active_alerts ?? 0,
          totalFindings: dashboard.kpis?.total_findings ?? 0,
          criticalFindings: dashboard.kpis?.critical_findings ?? 0,
          agentsActive: dashboard.agents_active ?? 0,
          agentsTotal: dashboard.agents_total ?? 0,
          hitlQueue: dashboard.hitl_queue_depth ?? 0,
        };
        if (dashboard.risk_trend?.length) {
          nextTrend = dashboard.risk_trend.map((p: { label: string; score: number }) => ({
            label: p.label,
            score: p.score,
          }));
        }
        if (dashboard.kpi_sparklines) {
          nextSparklines = { ...SPARK_FALLBACK, ...dashboard.kpi_sparklines };
        }
        if (Array.isArray(dashboard.priority_queue) && dashboard.priority_queue.length) {
          nextAlerts = dashboard.priority_queue.map(mapPriorityItem);
        }
      }

      if (dashboard && useOrchestrator) {
        if (Array.isArray(dashboard.vendor_risks)) {
          setVendorRisks(dashboard.vendor_risks);
        }
        if (Array.isArray(dashboard.threat_origins)) {
          setThreatOrigins(dashboard.threat_origins);
        }
      } else if (dashboard) {
        if (Array.isArray(dashboard.vendor_risks)) setVendorRisks(dashboard.vendor_risks);
        if (Array.isArray(dashboard.threat_origins)) setThreatOrigins(dashboard.threat_origins);
      }

      if (!useOrchestrator && agentHealthResult.status === "fulfilled") {
        const d = agentHealthResult.value;
        nextAgents = (d.agents ?? []).map((a: { name: string; status: string }) => ({
          name: a.name,
          status: normalizeAgentStatus(a.status),
        }));
        nextKpis = {
          ...nextKpis,
          agentsActive: nextAgents.filter((a) => isAgentLive(a.status)).length,
          agentsTotal: nextAgents.length || nextKpis.agentsTotal,
        };
      }

      if (executiveResult.status === "fulfilled") {
        const d = executiveResult.value;
        const cs = d.compliance_status as Record<string, number> | undefined;
        if (cs) {
          const vals = Object.values(cs);
          const avg = vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100) : null;
          nextKpis = { ...nextKpis, compliancePct: avg };
        }
        if (d.critical_summary?.length) {
          setCriticalSummary(d.critical_summary);
        }
      }

      if (hitlResult.status === "fulfilled") {
        const q = hitlResult.value;
        const depth = Array.isArray(q) ? q.length : 0;
        nextKpis = { ...nextKpis, hitlQueue: depth };
      }

      if (alertsResult.status === "fulfilled" && !nextAlerts.length) {
        const items = alertsResult.value;
        if (items.length) {
          nextAlerts = items
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
            .sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
            .slice(0, 12);
        }
      }

      if (aiBriefResult.status === "fulfilled") {
        const d = aiBriefResult.value;
        if (d.tabs) {
          setAiBrief({ headline: d.headline ?? "", tabs: d.tabs });
        }
      }

      setKpis(nextKpis);
      setTrend(nextTrend);
      setSparklines(nextSparklines);
      setAlerts(nextAlerts);
      setAgents(nextAgents);
      setMetricsSource(useOrchestrator ? "orchestrator" : "legacy");
      setUpdatedAt(new Date());
    };

    load().catch(() => {});
    return () => {
      cancelled = true;
    };
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
    metricsSource,
    displayName,
    initials,
    tenantId,
    refresh,
  };
}
