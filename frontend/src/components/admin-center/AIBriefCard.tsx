"use client";

import Link from "next/link";
import type { AlertEvent, DashboardKpis } from "@/hooks/useAdminDashboard";

type Props = {
  kpis: DashboardKpis;
  alerts: AlertEvent[];
  criticalSummary: Array<{ title: string; severity: string }>;
};

export function AIBriefCard({ kpis, alerts, criticalSummary }: Props) {
  const topAlert = alerts[0];
  const topCritical = criticalSummary[0];
  const headline = topAlert?.message ?? topCritical?.title ?? "Platform monitoring active";
  const severity = topAlert?.severity ?? topCritical?.severity ?? "info";

  const verdictColor =
    kpis.riskScore >= 70 ? "var(--r-sec1)" : kpis.riskScore >= 50 ? "var(--r-sec1)" : "var(--m3)";

  return (
    <div className="card brief-card" aria-label="AI Summary and Executive Brief">
      <div className="brief-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <svg className="icon" style={{ color: "var(--magenta)", width: 16, height: 16 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 3l1.4 4.3L18 8.6l-4.3 1.4L12 14.3l-1.4-4.3L6 8.6l4.6-1.3L12 3z" />
            </svg>
            <div className="t-title" style={{ fontSize: 13, margin: 0 }}>
              AI Executive Brief
            </div>
            <span className="pill-ai">Live</span>
          </div>
          <div className="mono t-muted" style={{ fontSize: 11, marginTop: 3 }}>
            {topAlert ? `${topAlert.source} · ${topAlert.time}` : "Awaiting correlated signals"}
          </div>
        </div>
        <span className="pill-live">Live</span>
      </div>

      <div className="brief-hero">
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
            <span className="brief-verdict-label" style={{ color: verdictColor }}>
              {kpis.riskLabel.toUpperCase()}
            </span>
            <span className="brief-verdict-score mono">{kpis.riskScore}</span>
            <span className={kpis.riskScore > 60 ? "delta-neg mono" : "delta-pos mono"}>
              {kpis.riskScore > 60 ? "↑ above target" : "↓ within target"}
            </span>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "4px 0 0", lineHeight: 1.45 }}>
            {headline}
            {severity === "critical" || severity === "high"
              ? " — immediate review recommended."
              : " — routine monitoring."}
          </p>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <span className="brief-exposure-value">{kpis.criticalFindings}</span>
          <span className="t-muted" style={{ display: "block", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            critical items
          </span>
        </div>
      </div>

      <ul style={{ listStyle: "none", margin: "0 0 10px", padding: 0, display: "flex", flexWrap: "wrap", gap: "4px 14px", fontSize: 11, color: "var(--text-muted)" }}>
        <li>{kpis.activeAlerts} active alerts · {kpis.hitlQueue} HITL pending</li>
        <li>{kpis.agentsActive} agents live</li>
      </ul>

      <div style={{ marginBottom: 10 }}>
        <span className="eyebrow" style={{ display: "block", marginBottom: 5 }}>
          Summary
        </span>
        <p className="brief-summary-text">
          Risk score is {kpis.riskScore}/100 with {kpis.criticalFindings} critical finding
          {kpis.criticalFindings === 1 ? "" : "s"} and {kpis.totalFindings} total findings across the tenant.
          {kpis.hitlQueue > 0
            ? ` ${kpis.hitlQueue} human-in-the-loop action${kpis.hitlQueue === 1 ? "" : "s"} await approval before automated containment can proceed.`
            : " No human gates are currently blocking automated response."}
        </p>
      </div>

      {kpis.hitlQueue > 0 && (
        <Link href="/investigation" className="brief-primary-action" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
          <div className="eyebrow" style={{ color: "var(--r-sec2)" }}>
            #1 · HITL Gate
          </div>
          <div className="mono t-title" style={{ fontSize: 12 }}>
            {kpis.hitlQueue} pending approval{kpis.hitlQueue === 1 ? "" : "s"}
          </div>
          <span className="t-muted" style={{ fontSize: 11 }}>
            Review queue →
          </span>
        </Link>
      )}

      {topCritical && (
        <Link href="/alerts" className="btn-ghost" style={{ display: "inline-block", marginTop: 4, textDecoration: "none" }}>
          View critical: {topCritical.title.slice(0, 40)}…
        </Link>
      )}
    </div>
  );
}
