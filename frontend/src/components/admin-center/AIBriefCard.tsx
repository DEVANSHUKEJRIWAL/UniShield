"use client";

import Link from "next/link";
import { useState } from "react";
import type { AlertEvent, DashboardKpis } from "@/hooks/useAdminDashboard";

type Tab = "exec" | "soc" | "compliance";

type AiBriefProp = {
  headline: string;
  tabs: { exec: string; soc: string; compliance: string };
} | null;

type Props = {
  kpis: DashboardKpis;
  alerts: AlertEvent[];
  criticalSummary: Array<{ title: string; severity: string }>;
  aiBrief?: AiBriefProp;
};

export function AIBriefCard({ kpis, alerts, criticalSummary, aiBrief }: Props) {
  const [tab, setTab] = useState<Tab>("exec");
  const topAlert = alerts[0];
  const topCritical = criticalSummary[0];
  const headline = aiBrief?.headline ?? topAlert?.message ?? topCritical?.title ?? "Platform monitoring active";
  const severity = topAlert?.severity ?? topCritical?.severity ?? "info";

  const verdictColor =
    kpis.riskScore >= 70 ? "var(--r-sec1)" : kpis.riskScore >= 50 ? "var(--r-sec1)" : "var(--m3)";

  const tabSummary =
    tab === "exec"
      ? aiBrief?.tabs.exec ??
        `Risk score is ${kpis.riskScore}/100 with ${kpis.criticalFindings} critical findings. ${kpis.compliancePct != null ? `Compliance posture averages ${kpis.compliancePct}%.` : ""}`
      : tab === "soc"
        ? aiBrief?.tabs.soc ??
          `${kpis.activeAlerts} open alerts, ${kpis.hitlQueue} HITL gates, ${kpis.agentsActive} agents live. Top signal: ${headline}.`
        : aiBrief?.tabs.compliance ??
          `Compliance coverage ${kpis.compliancePct ?? 82}% across RBI, DPDP, and PCI frameworks. ${kpis.criticalFindings} critical gaps require GRC review.`;

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

      <div className="ac-filter-wrap" style={{ marginBottom: 12 }}>
        {(
          [
            ["exec", "Executive"],
            ["soc", "SOC"],
            ["compliance", "Compliance"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`ac-filter-btn${tab === key ? " is-active" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="brief-hero">
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
            <span className="brief-verdict-label" style={{ color: verdictColor }}>
              {kpis.riskLabel.toUpperCase()}
            </span>
            <span className="brief-verdict-score mono">{kpis.riskScore}</span>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-secondary)", margin: "4px 0 0", lineHeight: 1.45 }}>
            {headline}
            {severity === "critical" || severity === "high" ? " — immediate review recommended." : " — routine monitoring."}
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
          {tab === "exec" ? "Executive summary" : tab === "soc" ? "SOC brief" : "Compliance brief"}
        </span>
        <p className="brief-summary-text">{tabSummary}</p>
      </div>

      {tab === "soc" && alerts.length > 1 && (
        <div style={{ marginBottom: 10 }}>
          <span className="eyebrow">Attack chain (signals)</span>
          <ol style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 11, color: "var(--text-secondary)" }}>
            {alerts.slice(0, 4).map((a) => (
              <li key={a.id}>
                {a.severity}: {a.message.slice(0, 60)}
              </li>
            ))}
          </ol>
        </div>
      )}

      {kpis.hitlQueue > 0 && (
        <Link href="/investigation" className="brief-primary-action" style={{ display: "block", textDecoration: "none", color: "inherit" }}>
          <div className="eyebrow" style={{ color: "var(--r-sec2)" }}>
            HITL Gate
          </div>
          <div className="mono t-title" style={{ fontSize: 12 }}>
            {kpis.hitlQueue} pending approval{kpis.hitlQueue === 1 ? "" : "s"}
          </div>
        </Link>
      )}
    </div>
  );
}
