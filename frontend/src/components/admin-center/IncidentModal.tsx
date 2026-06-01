"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { AlertEvent } from "@/hooks/useAdminDashboard";
import { assignAlert, updateAlertStatus } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Props = {
  alert: AlertEvent | null;
  onClose: () => void;
  onUpdated?: () => void;
};

export function IncidentModal({ alert, onClose, onUpdated }: Props) {
  const router = useRouter();
  const { token, email } = useAuth();
  const [busy, setBusy] = useState<string | null>(null);

  if (!alert) return null;

  const run = async (action: string, fn: () => Promise<unknown>) => {
    setBusy(action);
    try {
      await fn();
      toast.success(`Alert ${action}`);
      onUpdated?.();
      onClose();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="incident-modal-title"
      className="incident-modal-backdrop ac-fade-in"
      onClick={onClose}
    >
      <div className="card incident-modal ac-scale-in" onClick={(e) => e.stopPropagation()}>
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
          <button
            type="button"
            className="btn-accent"
            disabled={!!busy || !token}
            onClick={() =>
              run("acknowledged", () => updateAlertStatus(alert.id, token!, { status: "acknowledged" }))
            }
          >
            {busy === "acknowledged" ? "…" : "Acknowledge"}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={!!busy || !token}
            onClick={() =>
              run("assigned", () =>
                assignAlert(alert.id, token!, { assigned_to: email ?? "analyst@meridian.com" })
              )
            }
          >
            {busy === "assigned" ? "…" : "Assign analyst"}
          </button>
          <button
            type="button"
            className="btn-ghost"
            disabled={!!busy}
            onClick={() => {
              onClose();
              router.push(`/investigation${alert.findingId ? `?finding=${alert.findingId}` : ""}`);
            }}
          >
            Open investigation
          </button>
        </div>
      </div>
    </div>
  );
}
