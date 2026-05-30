"use client";

import { Sidebar } from "@/components/Sidebar";

export default function ReportingPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Reporting</h1>
        <p className="mt-2 text-[var(--text-secondary)]">Executive and regulatory report generation with CISO sign-off queue.</p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {["Board Summary", "CISO Brief", "RBI IT Framework"].map((r) => (
            <div key={r} className="obsidian-card">
              <p className="font-medium">{r}</p>
              <button className="mt-3 rounded bg-[var(--violet)] px-3 py-1 text-xs text-white">Generate</button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
