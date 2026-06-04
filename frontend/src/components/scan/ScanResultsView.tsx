"use client";

import { useMemo, useState } from "react";
import { RiskGauge } from "@/components/ui/RiskGauge";
import { FindingCard } from "@/components/scan/FindingCard";
import {
  blastScore,
  coerceList,
  formatWhen,
  parseCmaSnapshot,
  parseScrSnapshot,
  severityColor,
  type ScrFinding,
  type ScrSnapshot,
} from "@/lib/scr-parse";

type Props = {
  scr: ScrSnapshot;
  cma?: ScrSnapshot;
  reporting?: ScrSnapshot;
  workflowId: string;
  repoLabel?: string;
  completedAt?: string;
  startedAt?: string;
};

export function ScanResultsView({
  scr,
  cma,
  reporting,
  workflowId,
  repoLabel,
  completedAt,
  startedAt,
}: Props) {
  const parsed = parseScrSnapshot(scr);
  const cmaParsed = parseCmaSnapshot(cma);
  const gaps = [...parsed.complianceGaps, ...cmaParsed.complianceGaps];

  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [toolFilter, setToolFilter] = useState<string>("all");
  const [sortByBlast, setSortByBlast] = useState(true);

  const riskScore = Number(scr.risk_score ?? 0);
  const requiresApproval = Boolean(scr.requires_human_approval);
  const filesScanned = Number(scr.files_discovered ?? 0);
  const criticalCount = Number(scr.critical_count ?? 0);
  const tools = coerceList<string>(parsed.analysisStats.tools_invoked);

  const durationMin =
    startedAt && completedAt
      ? Math.max(1, Math.round((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 60000))
      : null;

  const findings = useMemo(() => {
    let list = [...parsed.findings] as ScrFinding[];
    if (severityFilter !== "all") {
      list = list.filter((f) => String(f.severity).toUpperCase() === severityFilter.toUpperCase());
    }
    if (toolFilter !== "all") {
      list = list.filter(
        (f) =>
          (f.tool ?? f.rule_id ?? "").toLowerCase().includes(toolFilter.toLowerCase()) ||
          toolFilter === "heuristic"
      );
    }
    if (sortByBlast) {
      list.sort((a, b) => blastScore(b) - blastScore(a));
    }
    return list;
  }, [parsed.findings, severityFilter, toolFilter, sortByBlast]);

  const attackSummary = parsed.attackPaths;
  const headline = `${criticalCount} critical issue${criticalCount === 1 ? "" : "s"} across ${filesScanned} files`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {requiresApproval && (
        <div
          className="ac-card"
          style={{
            borderColor: "var(--r-sec1)",
            background: "color-mix(in srgb, var(--r-sec1) 8%, transparent)",
            padding: "12px 16px",
          }}
        >
          <strong style={{ color: "var(--r-sec1)" }}>Requires human approval</strong>
          <span className="t-muted" style={{ marginLeft: 8, fontSize: 13 }}>
            High-risk findings must be reviewed before remediation actions run.
          </span>
        </div>
      )}

      <div className="ac-card" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 24, padding: 20 }}>
        <RiskGauge score={riskScore} size="lg" />
        <div>
          <h2 className="t-title" style={{ margin: "0 0 8px", fontSize: 20 }}>
            {headline}
          </h2>
          <p className="t-muted" style={{ margin: 0, fontSize: 13 }}>
            {repoLabel ?? workflowId}
            {durationMin != null ? ` · ${durationMin} min scan` : ""}
            {completedAt ? ` · ${formatWhen(completedAt)}` : ""}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            {cmaParsed.frameworks.map((fw) => (
              <span
                key={fw}
                className="mono"
                style={{
                  fontSize: 10,
                  padding: "4px 8px",
                  borderRadius: 6,
                  border: "1px solid var(--border-default)",
                }}
              >
                {fw}
              </span>
            ))}
          </div>
          {reporting?.executive_summary ? (
            <p style={{ marginTop: 12, fontSize: 13 }}>{String(reporting.executive_summary)}</p>
          ) : null}
        </div>
      </div>

      <div className="ac-card" style={{ padding: 16 }}>
        <div className="eyebrow">Attack path summary</div>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginTop: 8, fontSize: 13 }}>
          <span>
            <strong>{Number(attackSummary.total_paths ?? 0)}</strong> paths
          </span>
          <span>
            <strong>{Number(attackSummary.crown_jewel_paths ?? 0)}</strong> crown jewel
          </span>
          <span>
            Highest blast <strong>{Number(attackSummary.highest_blast_score ?? 0)}</strong>
          </span>
        </div>
      </div>

      <div className="ac-card" style={{ padding: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
          <h3 className="t-title" style={{ margin: 0, fontSize: 15 }}>
            Findings ({findings.length})
          </h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <select className="input" style={{ width: "auto", fontSize: 12 }} value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
              <option value="all">All severities</option>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select className="input" style={{ width: "auto", fontSize: 12 }} value={toolFilter} onChange={(e) => setToolFilter(e.target.value)}>
              <option value="all">All tools</option>
              {tools.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <input type="checkbox" checked={sortByBlast} onChange={(e) => setSortByBlast(e.target.checked)} />
              Sort by blast score
            </label>
          </div>
        </div>
        {findings.length === 0 ? (
          <p className="t-muted" style={{ fontSize: 13 }}>
            No findings match the current filters. Try clearing filters or re-scan with Semgrep rules enabled.
          </p>
        ) : (
          findings.map((f, i) => (
            <FindingCard
              key={f.finding_id ?? `${f.file_path}-${i}`}
              finding={f}
              remediationPlan={parsed.remediationPlan}
              complianceGaps={gaps}
            />
          ))
        )}
      </div>

      <div className="ac-card" style={{ padding: 16 }}>
        <h3 className="t-title" style={{ margin: "0 0 12px", fontSize: 15 }}>
          Secrets ({parsed.secrets.length})
        </h3>
        {parsed.secrets.length === 0 ? (
          <p className="t-muted" style={{ fontSize: 13 }}>
            No secrets detected in scannable paths (test/mock paths excluded).
          </p>
        ) : (
          <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
            <thead>
              <tr className="t-muted">
                <th style={{ textAlign: "left", padding: 8 }}>File</th>
                <th style={{ textAlign: "left", padding: 8 }}>Type</th>
                <th style={{ textAlign: "left", padding: 8 }}>Masked</th>
                <th style={{ textAlign: "left", padding: 8 }}>Entropy</th>
                <th style={{ textAlign: "left", padding: 8 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {parsed.secrets.map((s, i) => (
                <tr key={i} style={{ borderTop: "1px solid var(--border-default)" }}>
                  <td className="mono" style={{ padding: 8 }}>
                    {s.file_path}:{s.line_number}
                  </td>
                  <td style={{ padding: 8 }}>{s.secret_type}</td>
                  <td className="mono" style={{ padding: 8 }}>
                    {s.masked_value}
                  </td>
                  <td style={{ padding: 8 }}>{s.entropy_score?.toFixed(1)}</td>
                  <td style={{ padding: 8, color: s.verified_live ? "var(--r-sec1)" : "var(--m3)" }}>
                    {s.verified_live ? "Verified live" : "Unverified"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="ac-card" style={{ padding: 16 }}>
        <h3 className="t-title" style={{ margin: "0 0 12px", fontSize: 15 }}>
          Compliance
        </h3>
        {gaps.length === 0 ? (
          <p className="t-muted" style={{ fontSize: 13 }}>
            No compliance gaps mapped for this scan.
          </p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
            {cmaParsed.frameworks.map((fw) => {
              const fwGaps = gaps.filter((g) => g.framework === fw);
              const fails = fwGaps.filter((g) => g.status === "FAIL").length;
              return (
                <div key={fw} style={{ border: "1px solid var(--border-default)", borderRadius: 10, padding: 12 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{fw}</div>
                  <div className="t-muted" style={{ fontSize: 11, margin: "4px 0 8px" }}>
                    {fails} failing · {fwGaps.length - fails} pass/review
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
                    {fwGaps.slice(0, 5).map((g, i) => (
                      <li key={i} style={{ color: g.status === "FAIL" ? severityColor(g.severity ?? "HIGH") : undefined }}>
                        {g.control} — {g.category}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="ac-card" style={{ padding: 16 }}>
        <h3 className="t-title" style={{ margin: "0 0 12px", fontSize: 15 }}>
          Dependencies & SBOM
        </h3>
        {parsed.dependencies.length === 0 && Number(parsed.sbomSummary.components ?? 0) === 0 ? (
          <p className="t-muted" style={{ fontSize: 13 }}>
            No dependency manifest detected. Install Syft/Grype (
            <code>./scripts/install-scr-tools.sh</code>) and ensure package manifests exist in the repo root.
          </p>
        ) : (
          <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
            <thead>
              <tr className="t-muted">
                <th style={{ textAlign: "left", padding: 8 }}>Package</th>
                <th style={{ textAlign: "left", padding: 8 }}>Version</th>
                <th style={{ textAlign: "left", padding: 8 }}>CVE</th>
                <th style={{ textAlign: "left", padding: 8 }}>CVSS</th>
              </tr>
            </thead>
            <tbody>
              {parsed.dependencies.map((d, i) => (
                <tr key={i} style={{ borderTop: "1px solid var(--border-default)" }}>
                  <td style={{ padding: 8 }}>{d.package_name}</td>
                  <td className="mono" style={{ padding: 8 }}>
                    {d.version}
                  </td>
                  <td style={{ padding: 8 }}>{d.cve_id}</td>
                  <td style={{ padding: 8, color: severityColor(d.severity ?? "HIGH") }}>
                    {d.cvss_score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <footer className="t-muted mono" style={{ fontSize: 11, padding: "8px 0" }}>
        Tools: {tools.join(", ") || "—"} · Files scanned: {filesScanned} · Total findings:{" "}
        {String(scr.total_findings ?? findings.length)}
      </footer>
    </div>
  );
}
