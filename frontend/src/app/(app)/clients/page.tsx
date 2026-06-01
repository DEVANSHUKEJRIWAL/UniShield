"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchClients } from "@/lib/api";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";

export default function ClientsPage() {
  const { token, ready } = useAuth();
  const [clients, setClients] = useState<Array<{ id: string; name: string; industry: string; tier: string }>>([]);

  useEffect(() => {
    if (ready && token) fetchClients(token).then(setClients).catch(() => {});
  }, [ready, token]);

  return (
    <>
      <AdminPageHeader title="Clients" subtitle="Multi-tenant overview · PLATFORM_ADMIN" />

      <div className="ac-grid-2">
        {clients.map((c) => (
          <AnimatedCard key={c.id}>
            <p className="font-medium">{c.name}</p>
            <p className="mono mt-1 text-xs text-[var(--text-muted)]">
              {c.id} · {c.industry}
            </p>
            <p className="mono mt-2 text-xs text-[var(--green)]">Tier: {c.tier}</p>
          </AnimatedCard>
        ))}
      </div>
    </>
  );
}
