"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchDeploymentStatus } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";

export default function DeploymentPage() {
  const { token, ready } = useAuth();
  const [status, setStatus] = useState<{
    environment?: string;
    kubernetes?: boolean;
    components?: Record<string, { status?: string; uri?: string; code?: number }>;
  }>({});

  useEffect(() => {
    if (ready && token) fetchDeploymentStatus(token).then(setStatus).catch(() => {});
  }, [ready, token]);

  const components = Object.entries(status.components ?? {});

  return (
    <>
      <AdminPageHeader
        title="Deploy"
        subtitle={`Environment: ${status.environment ?? "dev"} · Kubernetes: ${status.kubernetes ? "yes" : "no"}`}
      />

      <div className="ac-grid-3">
        {components.map(([name, info]) => (
          <AnimatedCard key={name}>
            <p className="font-mono text-xs uppercase text-[var(--text-muted)]">{name.replace(/_/g, " ")}</p>
            <p className="mt-2 text-lg font-bold capitalize">{info.status ?? "unknown"}</p>
            {info.uri && (
              <p className="mt-1 truncate font-mono text-[10px] text-[var(--text-muted)]">{info.uri}</p>
            )}
          </AnimatedCard>
        ))}
      </div>
    </>
  );
}
