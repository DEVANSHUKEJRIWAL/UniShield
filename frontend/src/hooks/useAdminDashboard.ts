"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchWorkflowMetrics, type WorkflowMetrics } from "@/lib/workflows-api";
import { features } from "@/lib/features";

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

export type SeverityMix = {
  critical: number;
  high: number;
  medium: number;
  low: number;
};

export type WorkflowStats = {
  running: number;
  completed: number;
  failed: number;
  paused: number;
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

const EMPTY_SEVERITY_MIX: SeverityMix = { critical: 0, high: 0, medium: 0, low: 0 };

function normalizeAgentStatus(status: string): AgentRow["status"] {
  if (status === "running") return "running";
  if (status === "listening") return "listening";
  if (status === "error") return "error";
  return "idle";
}

function normalizeRiskScore(raw: number): number {
  return raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
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

function applyOrchestratorMetrics(metrics: WorkflowMetrics) {
  const kpis: DashboardKpis = {
    riskScore: normalizeRiskScore(metrics.kpis?.risk_score ?? 0),
    riskLabel: metrics.kpis?.risk_label ?? "Low",
    totalFindings: metrics.kpis?.total_findings ?? 0,
    criticalFindings: metrics.kpis?.critical_findings ?? 0,
    activeAlerts: metrics.kpis?.active_alerts ?? 0,
    agentsActive: metrics.agents_active ?? 0,
    agentsTotal: metrics.agents_total ?? 0,
    hitlQueue: metrics.kpis?.hitl_queue ?? metrics.paused_workflows ?? 0,
    compliancePct: metrics.kpis?.compliance_pct ?? null,
  };

  return {
    kpis,
    trend: metrics.risk_trend?.length
      ? metrics.risk_trend.map((p) => ({ label: p.label, score: p.score }))
      : [],
    sparklines: (metrics.kpi_sparklines ?? {
      risk: [],
      critical: [],
      findings: [],
      agents: [],
      compliance: [],
      hitl: [],
    }) as KpiSparklines,
    alerts: (metrics.priority_queue ?? []).map(mapWorkflowPriority),
    agents: (metrics.agents ?? []).map((a) => ({
      name: a.name,
      status: normalizeAgentStatus(a.status),
    })),
    vendorRisks: metrics.vendor_risks ?? [],
    threatOrigins: metrics.threat_origins ?? [],
    criticalSummary: metrics.critical_summary ?? [],
    aiBrief: metrics.ai_brief ?? null,
    severityMix: {
      critical: metrics.severity_mix?.critical ?? 0,
      high: metrics.severity_mix?.high ?? 0,
      medium: metrics.severity_mix?.medium ?? 0,
      low: metrics.severity_mix?.low ?? 0,
    } satisfies SeverityMix,
    workflowStats: {
      running: metrics.running_workflows ?? 0,
      completed: metrics.completed_workflows ?? 0,
      failed: metrics.failed_workflows ?? 0,
      paused: metrics.paused_workflows ?? 0,
    } satisfies WorkflowStats,
  };
}

export function useAdminDashboard(range: DashboardRange = "7d") {
  const { token, tenantId, ready, email } = useAuth();
  const orchMetricsEnabled = features.orchestratorDashboardMetrics;
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
  const [severityMix, setSeverityMix] = useState<SeverityMix>(EMPTY_SEVERITY_MIX);
  const [workflowStats, setWorkflowStats] = useState<WorkflowStats>({
    running: 0,
    completed: 0,
    failed: 0,
    paused: 0,
  });
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [metricsSource, setMetricsSource] = useState<DashboardMetricsSource>("legacy");
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;

    let cancelled = false;

    const load = async () => {
      if (!features.orchestratorUi || !orchMetricsEnabled) {
        setMetricsSource("legacy");
        setUpdatedAt(new Date());
        return;
      }

      const metricsResult = await Promise.allSettled([fetchWorkflowMetrics(tenantId, token)]);
      const metrics =
        metricsResult[0]?.status === "fulfilled" ? metricsResult[0].value : null;

      if (metrics?.available) {
        const next = applyOrchestratorMetrics(metrics);
        if (cancelled) return;
        setKpis(next.kpis);
        setTrend(next.trend);
        setSparklines(next.sparklines);
        setAlerts(next.alerts);
        setAgents(next.agents);
        setVendorRisks(next.vendorRisks);
        setThreatOrigins(next.threatOrigins);
        setCriticalSummary(next.criticalSummary);
        setAiBrief(next.aiBrief);
        setSeverityMix(next.severityMix);
        setWorkflowStats(next.workflowStats);
        setMetricsSource("orchestrator");
        setUpdatedAt(new Date());
        return;
      }

      if (cancelled) return;
      setMetricsSource("legacy");
      setUpdatedAt(new Date());
    };

    load().catch(() => {});
    const poll = orchMetricsEnabled
      ? window.setInterval(() => {
          load().catch(() => {});
        }, 30000)
      : undefined;

    return () => {
      cancelled = true;
      if (poll) window.clearInterval(poll);
    };
  }, [ready, token, tenantId, range, refreshKey, orchMetricsEnabled]);

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
    severityMix,
    workflowStats,
    updatedAt,
    metricsSource,
    displayName,
    initials,
    tenantId,
    refresh,
  };
}
