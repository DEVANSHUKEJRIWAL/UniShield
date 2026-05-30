"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { fetchReportingSummary, generateReport } from "@/lib/api";
import { GradientText } from "@/components/ui/primitives";

export default function ReportingPage() {
  const { token, tenantId, ready } = useAuth();
  const [summary, setSummary] = useState<{
    executive_narrative?: string;
    summary?: { total?: number; critical?: number; high?: number };
    recommended_reports?: string[];
  }>({});
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    if (ready && token && tenantId) {
      fetchReportingSummary(tenantId, token).then(setSummary).catch(() => {});
    }
  }, [ready, token, tenantId]);

  const reports = summary.recommended_reports ?? ["Board Summary", "CISO Brief", "RBI IT Framework"];

  const onGenerate = async (reportType: string) => {
    if (!token || !tenantId) return;
    setGenerating(reportType);
    try {
      const result = await generateReport(tenantId, token, reportType);
      toast.success(`${reportType} generated`, { description: result.message });
    } catch {
      toast.error("Report generation failed");
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Reporting</GradientText></h1>
      <p className="text-[var(--text-secondary)]">
        {summary.executive_narrative ?? "Executive and regulatory report generation with CISO sign-off queue."}
      </p>
      {summary.summary && (
        <div className="grid grid-cols-3 gap-4 font-mono text-sm">
          <div className="obsidian-card">Total: {summary.summary.total ?? 0}</div>
          <div className="obsidian-card">Critical: {summary.summary.critical ?? 0}</div>
          <div className="obsidian-card">High: {summary.summary.high ?? 0}</div>
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        {reports.map((r) => (
          <div key={r} className="obsidian-card">
            <p className="font-medium">{r}</p>
            <button
              disabled={generating === r}
              onClick={() => onGenerate(r)}
              className="mt-3 rounded bg-[var(--violet)] px-3 py-1 text-xs text-white disabled:opacity-50"
            >
              {generating === r ? "Generating..." : "Generate"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
