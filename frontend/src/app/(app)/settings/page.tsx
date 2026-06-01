"use client";

import { useAuth } from "@/lib/auth";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";

export default function SettingsPage() {
  const { role, tenantId, email } = useAuth();

  return (
    <>
      <AdminPageHeader title="Settings" subtitle="Account and tenant configuration" />

      <AnimatedCard className="max-w-lg">
        <p className="text-sm">
          <span className="text-[var(--text-muted)]">Email:</span> {email}
        </p>
        <p className="mt-2 text-sm">
          <span className="text-[var(--text-muted)]">Role:</span> {role}
        </p>
        <p className="mt-2 text-sm">
          <span className="text-[var(--text-muted)]">Tenant:</span> {tenantId}
        </p>
      </AnimatedCard>
    </>
  );
}
