"use client";

import { Sidebar } from "@/components/Sidebar";

export default function NetworkPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Network Security</h1>
        <div className="obsidian-card mt-6">
          <p className="mono text-sm text-[var(--text-secondary)]">workstation-42 → internal-api → db-prod-01 (crown jewel)</p>
          <div className="mt-4 flex items-center gap-4">
            {["workstation-42", "internal-api", "db-prod-01"].map((n, i) => (
              <div key={n} className="flex items-center gap-4">
                <div className="rounded border border-[var(--violet)] px-3 py-2 text-xs">{n}</div>
                {i < 2 && <span className="text-[var(--text-muted)]">→</span>}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
