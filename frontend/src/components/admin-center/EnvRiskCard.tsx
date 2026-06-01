"use client";

import type { DashboardKpis } from "@/hooks/useAdminDashboard";

type Props = { kpis: DashboardKpis };

export function EnvRiskCard({ kpis }: Props) {
  const score = kpis.riskScore;
  const circ = 301.6;
  const offset = circ * (1 - score / 100);
  const color = score >= 70 ? "var(--r-sec1)" : score >= 50 ? "var(--r-sec1)" : "var(--m3)";
  const ptsToTarget = Math.max(0, score - 60);

  const factors = [
    { name: "Alert Volume", score: Math.min(99, score + 8), worst: score >= 65 },
    { name: "Critical Findings", score: Math.min(99, kpis.criticalFindings * 12 + 20), worst: kpis.criticalFindings > 3 },
    { name: "Agent Coverage", score: Math.max(20, 100 - (kpis.agentsTotal - kpis.agentsActive) * 15), worst: false },
    { name: "HITL Backlog", score: Math.min(99, kpis.hitlQueue * 18 + 30), worst: kpis.hitlQueue > 2 },
  ].sort((a, b) => b.score - a.score);

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span className="t-title">Environment Risk</span>
        <span className="mono t-muted" style={{ fontSize: 11 }}>
          7d · live
        </span>
      </div>

      <div className="env-risk-gauge-wrap">
        <svg width="100" height="100" viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="48" fill="none" stroke="var(--progress-track)" strokeWidth="10" />
          <circle
            cx="60"
            cy="60"
            r="48"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            transform="rotate(-90 60 60)"
            strokeLinecap="round"
          />
          <text x="60" y="58" textAnchor="middle" fontSize="24" fontWeight="700" fill={color} fontFamily="IBM Plex Mono, monospace">
            {score}
          </text>
          <text x="60" y="72" textAnchor="middle" fontSize="11" fill="var(--text-muted)" fontFamily="IBM Plex Mono, monospace">
            /100
          </text>
        </svg>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 4 }}>
          <span className="env-risk-label">{kpis.riskLabel.toUpperCase()}</span>
          <span className={score > 60 ? "delta-neg mono" : "delta-pos mono"} style={{ fontSize: 11 }}>
            {score > 60 ? "↑ above target" : "↓ improving"}
          </span>
        </div>
      </div>

      <p className="t-muted" style={{ textAlign: "center", fontSize: 11, margin: "0 0 8px" }}>
        Target &lt;60 · {ptsToTarget} pt{ptsToTarget === 1 ? "" : "s"} to target
      </p>

      <div style={{ marginBottom: 10 }}>
        {factors.slice(0, 3).map((f) => (
          <div key={f.name} className={`env-factor${f.worst ? " is-worst" : ""}`}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>{f.name}</span>
              <span className="mono" style={{ fontWeight: 700, color: f.worst ? "var(--r-sec2)" : "var(--text-primary)" }}>
                {Math.round(f.score)}
              </span>
            </div>
            <div className="env-factor-bar">
              <span style={{ width: `${f.score}%`, background: f.worst ? "var(--r-sec2)" : "var(--purple-mid)" }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
