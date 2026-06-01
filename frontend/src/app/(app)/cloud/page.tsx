"use client";

import { useEffect, useState } from "react";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { useAuth } from "@/lib/auth";
import { fetchFindings } from "@/lib/api";

type FindingRow = {
  id: string;
  title: string;
  severity: string;
  agent_id?: string;
  description?: string;
};

export default function CloudPage() {
  const { token, tenantId, ready } = useAuth();
  const [findings, setFindings] = useState<FindingRow[]>([]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchFindings(tenantId, token)
      .then((data) => {
        const rows = (data.items ?? data ?? []) as FindingRow[];
        const cloudish = rows.filter((f) =>
          /cloud|s3|iam|eks|rds|network-security|vulnerability/i.test(
            `${f.agent_id ?? ""} ${f.title ?? ""}`
          )
        );
        setFindings(cloudish.length ? cloudish.slice(0, 8) : rows.slice(0, 4));
      })
      .catch(() => setFindings([]));
  }, [ready, token, tenantId]);

  return (
    <>
      <AdminPageHeader title="Cloud Security" subtitle="CSPM findings from live agent output" />

      <div className="ac-grid-2">
        {findings.length === 0 ? (
          <AnimatedCard>
            <p className="t-muted" style={{ fontSize: 13 }}>
              No cloud findings yet — run the orchestrator or vulnerability agent to populate.
            </p>
          </AnimatedCard>
        ) : (
          findings.map((r, i) => (
            <AnimatedCard key={r.id} delay={i * 0.06}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold">{r.title}</p>
                  <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">{r.agent_id ?? "agent"}</p>
                </div>
                <SeverityBadge severity={(r.severity as "critical" | "high" | "medium" | "low") ?? "medium"} />
              </div>
              {r.description ? (
                <p className="mt-3 text-sm text-[var(--text-secondary)]">{r.description.slice(0, 120)}</p>
              ) : null}
              <button type="button" className="btn-accent mt-4" style={{ padding: "6px 14px", fontSize: 11 }}>
                Remediate
              </button>
            </AnimatedCard>
          ))
        )}
      </div>
    </>
  );
}
