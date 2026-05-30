"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchClients } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";

export default function ClientsPage() {
  const { token, ready } = useAuth();
  const [clients, setClients] = useState<Array<{ id: string; name: string; industry: string; tier: string }>>([]);

  useEffect(() => {
    if (ready && token) fetchClients(token).then(setClients).catch(() => {});
  }, [ready, token]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Client Health</h1>
        <p className="mt-1 text-[var(--text-secondary)]">Multi-tenant overview — PLATFORM_ADMIN</p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {clients.map((c) => (
            <div key={c.id} className="obsidian-card">
              <p className="font-medium">{c.name}</p>
              <p className="mono mt-1 text-xs text-[var(--text-muted)]">{c.id} · {c.industry}</p>
              <p className="mono mt-2 text-xs text-[var(--success)]">Tier: {c.tier}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
