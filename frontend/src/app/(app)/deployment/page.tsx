"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchDeploymentStatus } from "@/lib/api";
import { GradientText } from "@/components/ui/primitives";
import { AnimatedCard } from "@/components/ui/AnimatedCard";

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
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Deployment Status</GradientText></h1>
      <p className="font-mono text-sm text-[var(--text-muted)]">
        Environment: {status.environment ?? "dev"} · Kubernetes: {status.kubernetes ? "yes" : "no"}
      </p>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {components.map(([name, info]) => (
          <AnimatedCard key={name}>
            <p className="font-mono text-xs uppercase text-[var(--text-muted)]">{name.replace(/_/g, " ")}</p>
            <p className="mt-2 text-lg font-bold capitalize">{info.status ?? "unknown"}</p>
            {info.uri && <p className="mt-1 truncate font-mono text-[10px] text-[var(--text-muted)]">{info.uri}</p>}
          </AnimatedCard>
        ))}
      </div>
    </div>
  );
}
