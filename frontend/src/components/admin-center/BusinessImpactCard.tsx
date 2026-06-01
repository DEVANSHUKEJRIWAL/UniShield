"use client";

import { useState } from "react";
import type { DashboardKpis } from "@/hooks/useAdminDashboard";

type Props = {
  kpis: DashboardKpis;
  range: string;
};

type Row = {
  id: string;
  label: string;
  val: number;
  pct: number;
  color: string;
  detail: string;
  impact: string;
};

export function BusinessImpactCard({ kpis, range }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const rows: Row[] = [
    {
      id: "alerts",
      label: "Open alerts",
      val: kpis.activeAlerts,
      pct: Math.min(100, kpis.activeAlerts * 8),
      color: "var(--r-sec2)",
      detail: `${kpis.activeAlerts} alerts require triage within SLA windows.`,
      impact: kpis.activeAlerts > 3 ? "Customer-facing fraud risk elevated" : "Within normal operating bounds",
    },
    {
      id: "critical",
      label: "Critical findings",
      val: kpis.criticalFindings,
      pct: Math.min(100, kpis.criticalFindings * 12),
      color: "var(--r-sec1)",
      detail: `${kpis.criticalFindings} crown-jewel or credential exposure items.`,
      impact: kpis.criticalFindings > 0 ? "Regulatory notification may be required (RBI/DPDP)" : "No critical regulatory triggers",
    },
    {
      id: "hitl",
      label: "HITL queue",
      val: kpis.hitlQueue,
      pct: Math.min(100, kpis.hitlQueue * 20),
      color: "var(--purple-mid)",
      detail: `${kpis.hitlQueue} agent actions awaiting human approval.`,
      impact: kpis.hitlQueue > 0 ? "Automated response blocked until analyst sign-off" : "All automated playbooks cleared",
    },
    {
      id: "findings",
      label: "Total findings",
      val: kpis.totalFindings,
      pct: Math.min(100, kpis.totalFindings * 3),
      color: "var(--m3)",
      detail: `${kpis.totalFindings} correlated findings in ${range} window.`,
      impact: `${kpis.agentsActive} live agents contributing to detection coverage`,
    },
  ];

  return (
    <div className="card business-impact-card">
      <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
        Business Impact · {range}
      </div>
      <div className="business-impact-summary">
        <strong>{kpis.criticalFindings} critical</strong> · {kpis.totalFindings} total findings · {kpis.activeAlerts} open alerts
      </div>
      <ul className="business-impact-list">
        {rows.map((row) => {
          const open = expanded === row.id;
          return (
            <li key={row.id} className={`business-impact-row${open ? " is-open" : ""}`}>
              <button
                type="button"
                className="business-impact-toggle"
                onClick={() => setExpanded(open ? null : row.id)}
                aria-expanded={open}
              >
                <span className="business-impact-label">{row.label}</span>
                <span className="mono t-title">{row.val}</span>
              </button>
              <div className="progress-track">
                <div className="progress-fill ac-animate-width" style={{ width: `${row.pct}%`, background: row.color }} />
              </div>
              {open ? (
                <div className="business-impact-detail ac-reveal">
                  <p>{row.detail}</p>
                  <p className="mono" style={{ color: row.color, fontSize: 11 }}>
                    {row.impact}
                  </p>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
