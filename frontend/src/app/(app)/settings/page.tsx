"use client";

import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";

export default function SettingsPage() {
  const { role, tenantId, email } = useAuth();
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Settings</h1>
        <div className="obsidian-card mt-6 max-w-lg">
          <p className="text-sm"><span className="text-[var(--text-muted)]">Email:</span> {email}</p>
          <p className="mt-2 text-sm"><span className="text-[var(--text-muted)]">Role:</span> {role}</p>
          <p className="mt-2 text-sm"><span className="text-[var(--text-muted)]">Tenant:</span> {tenantId}</p>
        </div>
      </main>
    </div>
  );
}
