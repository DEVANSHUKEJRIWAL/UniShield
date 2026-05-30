"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { downloadReport, fetchReports, fetchReportingSummary, generateReport } from "@/lib/api";
import { GradientText } from "@/components/ui/primitives";

type ReportRow = { id: string; report_type: string; status: string; created_at: string };

export default function ReportingPage() {
  const { token, tenantId, ready } = useAuth();
  const [summary, setSummary] = useState<{
    executive_narrative?: string;
    summary?: { total?: number; critical?: number; high?: number };
    recommended_reports?: string[];
  }>({});
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);

  const refresh = () => {
    if (!token || !tenantId) return;
    fetchReportingSummary(tenantId, token).then(setSummary).catch(() => {});
    fetchReports(tenantId, token).then(setReports).catch(() => {});
  };

  useEffect(() => {
    if (ready && token && tenantId) refresh();
  }, [ready, token, tenantId]);

  const reportTypes = summary.recommended_reports ?? ["Board Summary", "CISO Brief", "Analyst Report"];

  const onGenerate = async (reportType: string) => {
    if (!token || !tenantId) return;
    setGenerating(reportType);
    try {
      const result = await generateReport(tenantId, token, reportType);
      toast.success(`${reportType} generated`, { description: result.message });
      refresh();
    } catch {
      toast.error("Report generation failed");
    } finally {
      setGenerating(null);
    }
  };

  const onDownload = async (reportId: string, name: string) => {
    if (!token) return;
    try {
      const blob = await downloadReport(reportId, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name.replace(/\s+/g, "_").toLowerCase()}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
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
        {reportTypes.map((r) => (
          <div key={r} className="obsidian-card">
            <p className="font-medium">{r}</p>
            <button
              disabled={generating === r}
              onClick={() => onGenerate(r)}
              className="mt-3 rounded bg-[var(--violet)] px-3 py-1 text-xs text-white disabled:opacity-50"
            >
              {generating === r ? "Generating..." : "Generate PDF"}
            </button>
          </div>
        ))}
      </div>
      {reports.length > 0 && (
        <div className="obsidian-card">
          <h2 className="mb-3 font-bold">Generated Reports</h2>
          <div className="space-y-2">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between font-mono text-xs">
                <span>{r.report_type} · {r.status}</span>
                <button onClick={() => onDownload(r.id, r.report_type)} className="text-[var(--violet-light)]">Download</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
