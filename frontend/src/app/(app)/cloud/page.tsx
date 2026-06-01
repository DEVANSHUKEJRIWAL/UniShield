"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { useAuth } from "@/lib/auth";
import { fetchFindings, runCspmScan } from "@/lib/api";

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
  const [scanning, setScanning] = useState(false);

  const loadFindings = useCallback(() => {
    if (!token || !tenantId) return;
    fetchFindings(tenantId, token)
      .then((data) => {
        const rows = (data.items ?? data ?? []) as FindingRow[];
        const cloudish = rows.filter((f) =>
          /cloud|s3|iam|eks|rds|network-security|vulnerability|cspm|guardduty/i.test(
            `${f.agent_id ?? ""} ${f.title ?? ""}`
          )
        );
        setFindings(cloudish.length ? cloudish.slice(0, 8) : rows.slice(0, 4));
      })
      .catch(() => setFindings([]));
  }, [token, tenantId]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    loadFindings();
  }, [ready, token, tenantId, loadFindings]);

  const handleCspmScan = async () => {
    if (!token || !tenantId) return;
    setScanning(true);
    try {
      const result = await runCspmScan(tenantId, token);
      toast.success(`CSPM scan complete — ${result.persisted_findings?.length ?? 0} findings`);
      loadFindings();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "CSPM scan failed");
    } finally {
      setScanning(false);
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Cloud Security"
        subtitle="CSPM findings from GuardDuty connector and live agent output"
        toolbar={
          <button type="button" className="btn-accent" disabled={scanning} onClick={handleCspmScan}>
            {scanning ? "Scanning AWS…" : "Run CSPM Scan"}
          </button>
        }
      />

      <div className="ac-grid-2">
        {findings.length === 0 ? (
          <AnimatedCard>
            <p className="t-muted" style={{ fontSize: 13 }}>
              No cloud findings yet — run CSPM scan or the orchestrator to populate.
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
