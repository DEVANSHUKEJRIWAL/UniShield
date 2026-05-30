"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchExecutiveDashboard } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";

export default function ExecutiveDashboardPage() {
  const { token, tenantId } = useAuth();
  const [data, setData] = useState<{ risk_trend?: Array<{ date: string; score: number }>; critical_summary?: Array<{ title: string; severity: string }>; compliance_status?: Record<string, number> }>({});

  useEffect(() => {
    if (token && tenantId) {
      fetchExecutiveDashboard(tenantId, token).then(setData).catch(() => {});
    }
  }, [token, tenantId]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Executive Dashboard</h1>
        <p className="mt-1 text-[var(--text-secondary)]">Board-level risk summary</p>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="obsidian-card">
            <h2 className="font-semibold">Risk Trend</h2>
            <div className="mt-4 space-y-2">
              {(data.risk_trend ?? []).map((p) => (
                <div key={p.date} className="flex items-center gap-3">
                  <span className="mono w-16 text-xs">{p.date}</span>
                  <div className="h-2 flex-1 rounded bg-[var(--bg-surface)]">
                    <div className="h-2 rounded bg-[var(--violet)]" style={{ width: `${p.score * 100}%` }} />
                  </div>
                  <span className="mono text-xs">{Math.round(p.score * 100)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="obsidian-card">
            <h2 className="font-semibold">Critical Findings</h2>
            <ul className="mt-4 space-y-2">
              {(data.critical_summary ?? []).map((f, i) => (
                <li key={i} className="text-sm text-[var(--text-secondary)]">
                  <span className="mono mr-2 text-[var(--danger)]">{f.severity}</span>{f.title}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}
