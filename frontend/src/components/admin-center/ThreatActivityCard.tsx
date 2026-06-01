"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AlertEvent, TrendPoint } from "@/hooks/useAdminDashboard";

type Props = {
  alerts: AlertEvent[];
  trend: TrendPoint[];
};

export function ThreatActivityCard({ alerts, trend }: Props) {
  return (
    <div className="card">
      <div className="t-title" style={{ fontSize: 13 }}>
        Threat Activity · 7d
      </div>
      <div className="t-muted" style={{ fontSize: 11, margin: "4px 0 12px" }}>
        Risk trend and live alert feed
      </div>

      <div style={{ marginBottom: 16 }}>
        <span className="activity-chart-title eyebrow">Risk trend</span>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={trend}>
            <defs>
              <linearGradient id="acRiskGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--purple-mid)" stopOpacity={0.35} />
                <stop offset="100%" stopColor="var(--purple-mid)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="label" stroke="var(--text-muted)" fontSize={10} />
            <YAxis stroke="var(--text-muted)" fontSize={10} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                background: "var(--surface-card)",
                border: "1px solid var(--border-dim)",
                borderRadius: 8,
                fontSize: 11,
              }}
            />
            <Area type="monotone" dataKey="score" stroke="var(--r-sec1)" fill="url(#acRiskGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <span className="activity-chart-title eyebrow">Live feed</span>
      <div style={{ maxHeight: 200, overflowY: "auto" }}>
        {(alerts.length ? alerts : [{ id: "0", severity: "info" as const, message: "Awaiting live events…", time: "now", source: "system" }]).map((a) => (
          <div key={a.id} className="live-feed-row">
            <span
              className="sev-dot"
              style={{
                marginTop: 5,
                background:
                  a.severity === "critical"
                    ? "var(--r-sec2)"
                    : a.severity === "high"
                      ? "var(--r-sec1)"
                      : "var(--purple-mid)",
              }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ color: "var(--text-primary)", fontSize: 12 }}>{a.message}</div>
              <div className="mono t-muted" style={{ fontSize: 11, marginTop: 2 }}>
                {a.source} · {a.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
