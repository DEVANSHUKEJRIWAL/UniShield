"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import { downloadReport, fetchReports, fetchReportingSummary, generateReport } from "@/lib/api";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { AnimatedCard } from "@/components/ui/AnimatedCard";

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
    if (!ready || !token || !tenantId) return;
    fetchReportingSummary(tenantId, token).then(setSummary).catch(() => {});
    fetchReports(tenantId, token).then(setReports).catch(() => {});
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
    <>
      <AdminPageHeader
        title="Reporting"
        subtitle={
          summary.executive_narrative ??
          "Executive and regulatory report generation with CISO sign-off queue."
        }
      />

      {summary.summary && (
        <div className="ac-grid-3 font-mono text-sm">
          <AnimatedCard>Total: {summary.summary.total ?? 0}</AnimatedCard>
          <AnimatedCard>Critical: {summary.summary.critical ?? 0}</AnimatedCard>
          <AnimatedCard>High: {summary.summary.high ?? 0}</AnimatedCard>
        </div>
      )}

      <div className="ac-grid-3">
        {reportTypes.map((r) => (
          <AnimatedCard key={r}>
            <p className="font-medium">{r}</p>
            <button
              type="button"
              disabled={generating === r}
              onClick={() => onGenerate(r)}
              className="btn-accent mt-3"
              style={{ padding: "6px 14px", fontSize: 12 }}
            >
              {generating === r ? "Generating…" : "Generate PDF"}
            </button>
          </AnimatedCard>
        ))}
      </div>

      {reports.length > 0 && (
        <AnimatedCard>
          <h2 className="ac-section-title">Generated Reports</h2>
          <div className="space-y-2">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between font-mono text-xs">
                <span>
                  {r.report_type} · {r.status}
                </span>
                <button
                  type="button"
                  onClick={() => onDownload(r.id, r.report_type)}
                  className="btn-ghost"
                  style={{ padding: "4px 12px", fontSize: 11 }}
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        </AnimatedCard>
      )}
    </>
  );
}
