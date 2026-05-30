"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchCompliance } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { ComplianceHeatmap } from "@/components/ComplianceHeatmap";

export default function CompliancePage() {
  const { token, tenantId } = useAuth();
  const [framework, setFramework] = useState("NIST_CSF_2");
  const [data, setData] = useState<{ controls?: Array<{ id: string; title: string; status: "implemented" | "partial" | "gap" }>; coverage_pct?: number }>({});

  useEffect(() => {
    if (token && tenantId) fetchCompliance(tenantId, framework, token).then(setData).catch(() => {});
  }, [token, tenantId, framework]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Compliance</h1>
          <select value={framework} onChange={(e) => setFramework(e.target.value)} className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-1 text-sm">
            {["RBI_IT_FRAMEWORK_2023", "SEBI_CSCRF", "DPDP_ACT_2023", "PCI_DSS_V4", "NIST_CSF_2", "ISO_27001_2022"].map((f) => (
              <option key={f} value={f}>{f.replace(/_/g, " ")}</option>
            ))}
          </select>
          <span className="mono text-sm text-[var(--violet)]">{Math.round((data.coverage_pct ?? 0) * 100)}% coverage</span>
        </div>
        <div className="mt-6">
          <ComplianceHeatmap framework={framework} controls={data.controls ?? []} />
        </div>
      </main>
    </div>
  );
}
