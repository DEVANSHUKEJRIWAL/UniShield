"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchAlerts } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";

interface Alert { id: string; title: string; severity: string; status: string; assigned_to: string | null; source: string; created_at: string; }

export default function AlertsPage() {
  const { token, tenantId } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (token && tenantId) fetchAlerts(tenantId, token).then(setAlerts).catch(() => {});
  }, [token, tenantId]);

  const filtered = filter ? alerts.filter((a) => a.severity === filter) : alerts;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Alert Management</h1>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-1 text-sm">
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
          </select>
        </div>
        <div className="mt-6 space-y-3">
          {filtered.map((a) => (
            <div key={a.id} className="obsidian-card flex items-center justify-between">
              <div>
                <p className="font-medium">{a.title}</p>
                <p className="mono mt-1 text-xs text-[var(--text-muted)]">{a.source} · {a.status}</p>
              </div>
              <span className="mono text-xs uppercase" style={{ color: a.severity === "critical" ? "var(--danger)" : "var(--warning)" }}>{a.severity}</span>
            </div>
          ))}
          {!filtered.length && <p className="text-[var(--text-muted)]">No alerts — run ./scripts/seed-local.sh</p>}
        </div>
      </main>
    </div>
  );
}
