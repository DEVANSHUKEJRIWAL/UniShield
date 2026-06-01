"use client";

import CountUp from "react-countup";
import { KpiSparkline } from "./KpiSparkline";
import type { DashboardKpis, KpiSparklines } from "@/hooks/useAdminDashboard";

type Range = "24h" | "7d" | "30d";

type Props = {
  kpis: DashboardKpis;
  sparklines: KpiSparklines;
  range: Range;
  onRangeChange: (r: Range) => void;
  updatedLabel?: string;
  onDrill?: (key: string) => void;
};

function riskStatus(score: number): { label: string; kind: string; color: string } {
  if (score >= 70) return { label: "Elevated", kind: "warn", color: "var(--r-sec1)" };
  if (score >= 50) return { label: "Moderate", kind: "warn", color: "var(--r-sec1)" };
  return { label: "Healthy", kind: "good", color: "var(--m3)" };
}

export function AdminKpiStrip({ kpis, sparklines, range, onRangeChange, updatedLabel, onDrill }: Props) {
  const risk = riskStatus(kpis.riskScore);
  const critStatus = kpis.criticalFindings > 5 ? "bad" : kpis.criticalFindings > 0 ? "warn" : "good";
  const compliance = kpis.compliancePct ?? 82;

  const cells = [
    {
      key: "risk",
      eyebrow: "Risk Score",
      val: kpis.riskScore,
      suffix: "",
      color: risk.color,
      spark: sparklines.risk,
      status: risk.label,
      statusKind: risk.kind,
      delta: kpis.riskScore > 60 ? "↑ elevated" : "↓ improving",
      deltaKind: kpis.riskScore > 60 ? "neg" : "pos",
      sub: `Target <strong>&lt;60</strong> · ${kpis.totalFindings} findings`,
    },
    {
      key: "critical",
      eyebrow: "Critical",
      val: kpis.criticalFindings,
      suffix: "",
      color: "var(--r-sec2)",
      spark: sparklines.critical,
      status: kpis.criticalFindings > 0 ? "Above baseline" : "Clear",
      statusKind: critStatus,
      delta: `${kpis.activeAlerts} open alerts`,
      deltaKind: kpis.criticalFindings > 0 ? "neg" : "pos",
      sub: `<strong>${kpis.hitlQueue}</strong> in HITL queue`,
    },
    {
      key: "findings",
      eyebrow: "Findings",
      val: kpis.totalFindings,
      suffix: "",
      color: "var(--r-sec1)",
      spark: sparklines.findings,
      status: "Tracked",
      statusKind: "neutral",
      delta: `${kpis.agentsActive} agents scanning`,
      deltaKind: "neutral",
      sub: `Live from <strong>${kpis.agentsTotal || kpis.agentsActive}</strong> agents`,
    },
    {
      key: "agents",
      eyebrow: "Agents Live",
      val: kpis.agentsActive,
      suffix: "",
      color: "var(--m3)",
      spark: sparklines.agents,
      status: "On track",
      statusKind: "good",
      delta: `/${kpis.agentsTotal || "—"}`,
      deltaKind: "neutral",
      sub: "Orchestrator + specialist agents",
    },
    {
      key: "compliance",
      eyebrow: "Compliance",
      val: compliance,
      suffix: "%",
      color: "var(--purple-mid)",
      spark: sparklines.compliance,
      status: compliance >= 85 ? "On target" : "Below target",
      statusKind: compliance >= 85 ? "good" : "warn",
      delta: kpis.compliancePct != null ? "from frameworks" : "estimated",
      deltaKind: "neutral",
      sub: "PCI · SOC2 · RBI/DPDP",
    },
    {
      key: "hitl",
      eyebrow: "HITL Queue",
      val: kpis.hitlQueue,
      suffix: "",
      color: kpis.hitlQueue > 0 ? "var(--r-sec1)" : "var(--m3)",
      spark: sparklines.hitl,
      status: kpis.hitlQueue > 0 ? "Needs action" : "Clear",
      statusKind: kpis.hitlQueue > 0 ? "warn" : "good",
      delta: kpis.hitlQueue > 0 ? "pending approval" : "no gates",
      deltaKind: kpis.hitlQueue > 0 ? "neg" : "pos",
      sub: `<strong>${kpis.activeAlerts}</strong> active alerts`,
    },
  ];

  return (
    <div className="kpi-strip-wrap ac-stagger-in">
      <div className="kpi-strip-head">
        <span className="eyebrow">Key metrics</span>
        <div className="kpi-range-toggle" role="tablist" aria-label="KPI time range">
          {(["24h", "7d", "30d"] as Range[]).map((r) => (
            <button
              key={r}
              type="button"
              className={`kpi-range-btn${range === r ? " is-active" : ""}`}
              onClick={() => onRangeChange(r)}
            >
              {r}
            </button>
          ))}
        </div>
        <span className="kpi-updated">{updatedLabel ?? "Updated just now"}</span>
      </div>
      <div className="kpi-strip">
        {cells.map((c, i) => (
          <button
            key={c.key}
            type="button"
            className="kpi-cell ac-fade-up"
            style={{ animationDelay: `${i * 60}ms` }}
            onClick={() => onDrill?.(c.key)}
            aria-label={`${c.eyebrow} ${c.val}${c.suffix}`}
          >
            <div className="kpi-cell-top">
              <span className="eyebrow">{c.eyebrow}</span>
              <span className={`kpi-status kpi-status--${c.statusKind}`}>{c.status}</span>
            </div>
            <div className="kpi-cell-body">
              <div>
                <div className="val" style={{ color: c.color }}>
                  <CountUp end={c.val} duration={1.2} suffix={c.suffix} decimals={0} />
                </div>
                <span className={`delta-${c.deltaKind}`}>{c.delta}</span>
              </div>
              <KpiSparkline data={c.spark} color={c.color} />
            </div>
            <div className="kpi-sub" dangerouslySetInnerHTML={{ __html: c.sub }} />
          </button>
        ))}
      </div>
    </div>
  );
}
