"use client";

import type { AlertEvent } from "@/hooks/useAdminDashboard";

type Props = {
  alert: AlertEvent | null;
  onClose: () => void;
};

export function IncidentModal({ alert, onClose }: Props) {
  if (!alert) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="incident-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        background: "rgba(15, 10, 30, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ maxWidth: 480, width: "100%" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div>
            <div className="eyebrow">Incident workflow</div>
            <h2 id="incident-modal-title" className="t-title" style={{ fontSize: 16, margin: "4px 0" }}>
              {alert.message}
            </h2>
          </div>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <p className="t-muted" style={{ fontSize: 12, marginTop: 8 }}>
          Source: <span className="mono">{alert.source}</span> · Severity:{" "}
          <span className="mono">{alert.severity}</span> · {alert.time}
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 16 }}>
          <button type="button" className="btn-accent">
            Acknowledge
          </button>
          <button type="button" className="btn-ghost">
            Assign analyst
          </button>
          <button type="button" className="btn-ghost">
            Open investigation
          </button>
        </div>
      </div>
    </div>
  );
}
