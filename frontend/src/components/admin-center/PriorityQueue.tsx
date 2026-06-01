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
  onSelect?: (alert: AlertEvent) => void;
};

export function PriorityQueue({ alerts, onSelect }: Props) {
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
        items.map((a) =>
          onSelect ? (
            <button
              key={a.id}
              type="button"
              className="leader-row--clickable"
              style={{ width: "100%", border: "none", background: "transparent", cursor: "pointer", textAlign: "left", font: "inherit", color: "inherit" }}
              onClick={() => onSelect(a)}
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
            </button>
          ) : (
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
            </Link>
          )
        )
      )}
    </div>
  );
}
