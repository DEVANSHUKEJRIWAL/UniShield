"use client";

import type { AlertEvent } from "@/hooks/useAdminDashboard";

const SEV_COLOR: Record<string, string> = {
  critical: "var(--r-sec2)",
  high: "var(--r-sec1)",
  medium: "var(--purple-mid)",
  low: "var(--m3)",
  info: "var(--r-sys)",
};

const SEV_LABEL: Record<string, string> = {
  critical: "CRITICAL",
  high: "HIGH",
  medium: "MEDIUM",
  low: "OK",
  info: "INFO",
};

type Props = {
  alerts: AlertEvent[];
  onSelect?: (id: string) => void;
};

export function ThreatStrip({ alerts, onSelect }: Props) {
  const items = alerts.length
    ? alerts.slice(0, 6)
    : [{ id: "0", severity: "info" as const, message: "No active alerts — platform monitoring", time: "", source: "system" }];

  return (
    <div className="threat-strip" role="region" aria-label="Priority threat intel">
      <span className="threat-strip-label">INTEL</span>
      <div className="threat-items">
        {items.map((a) => {
          const color = SEV_COLOR[a.severity] ?? "var(--lavender)";
          const label = SEV_LABEL[a.severity] ?? a.severity.toUpperCase();
          const content = (
            <>
              <span className="sev-dot" style={{ background: color }} />
              <span style={{ color }}>{label}</span>
              <span>{a.message.slice(0, 48)}{a.message.length > 48 ? "…" : ""}</span>
            </>
          );
          if (onSelect && a.id !== "0") {
            return (
              <button key={a.id} type="button" className="threat-item" onClick={() => onSelect(a.id)}>
                {content}
              </button>
            );
          }
          return (
            <div key={a.id} className="threat-item">
              {content}
            </div>
          );
        })}
      </div>
    </div>
  );
}
