"use client";

import { Sidebar } from "@/components/Sidebar";

export default function InvestigationPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Investigation</h1>
        <div className="obsidian-card mt-6">
          <h2 className="font-semibold">Credential Exposure — Meridian Financial</h2>
          <div className="mt-4 border-l-2 border-[var(--violet)] pl-4">
            <p className="mono text-xs text-[var(--text-muted)]">T+0 — Dark web agent detected credential dump</p>
            <p className="mono mt-2 text-xs text-[var(--text-muted)]">T+5m — HITL escalation triggered</p>
            <p className="mono mt-2 text-xs text-[var(--text-muted)]">T+12m — Forensics agent extracted 3 IOCs</p>
          </div>
        </div>
      </main>
    </div>
  );
}
