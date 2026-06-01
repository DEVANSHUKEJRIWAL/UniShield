"use client";

import Link from "next/link";
import type { AlertEvent } from "@/hooks/useAdminDashboard";

const SEV_SHORT: Record<string, string> = {
  critical: "P1",
  high: "P2",
  medium: "P3",
  low: "P3",
  info: "—",
};

const SEV_COLOR: Record<string, string> = {
  critical: "var(--r-sec2)",
  high: "var(--r-sec1)",
  medium: "var(--lavender)",
  low: "var(--lavender)",
  info: "var(--text-muted)",
};

type Props = {
  alerts: AlertEvent[];
};

export function PriorityQueue({ alerts }: Props) {
  const items = alerts.slice(0, 5);

  return (
    <div className="card">
      <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
        Priority Queue
      </div>
      {items.length === 0 ? (
        <p className="t-muted" style={{ fontSize: 12 }}>
          No open alerts — platform clear
        </p>
      ) : (
        items.map((a) => (
          <Link
            key={a.id}
            href="/alerts"
            className="leader-row--clickable"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="leader-avatar" style={{ color: SEV_COLOR[a.severity] }}>
              {SEV_SHORT[a.severity]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="t-title" style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {a.message}
              </div>
              <div className="t-muted mono" style={{ fontSize: 11 }}>
                {a.source} · {a.time}
              </div>
            </div>
            <span className="mono" style={{ color: SEV_COLOR[a.severity], fontSize: 11, fontWeight: 600 }}>
              {a.severity === "critical" ? "9.8" : a.severity === "high" ? "8.1" : "7.2"}
            </span>
          </Link>
        ))
      )}
    </div>
  );
}
