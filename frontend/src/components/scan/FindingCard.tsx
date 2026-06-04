"use client";

import { useState } from "react";
import { AttackPathVisualizer } from "@/components/scan/AttackPathVisualizer";
import {
  blastScore,
  findingDescription,
  fixComplexity,
  remediationSteps,
  severityColor,
  type ScrFinding,
} from "@/lib/scr-parse";

type Props = {
  finding: ScrFinding;
  remediationPlan: string[];
  complianceGaps: Array<{ control?: string; framework?: string; status?: string }>;
  crownJewelPaths?: string[];
  onMarkTestSecret?: never;
};

export function FindingCard({ finding, remediationPlan, complianceGaps, crownJewelPaths }: Props) {
  const [open, setOpen] = useState(false);
  const isCrown = crownJewelPaths?.some((p) => finding.file_path?.includes(p)) ?? finding.crown_jewel_boost;
  const likelyFp = (finding.false_positive_score ?? 0) > 0.7;
  const steps = remediationSteps(finding, remediationPlan);
  const complexity = fixComplexity(finding);
  const relatedGap = complianceGaps.find((g) => g.control && finding.cwe_id?.includes("89"));

  return (
    <article
      className="ac-card"
      style={{
        marginBottom: 12,
        borderLeft: `4px solid ${severityColor(finding.severity ?? "LOW")}`,
        padding: "14px 16px",
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                letterSpacing: "0.04em",
                color: severityColor(finding.severity ?? "LOW"),
              }}
            >
              {(finding.severity ?? "LOW").toUpperCase()}
            </span>
            {finding.cwe_id && (
              <a
                href={`https://cwe.mitre.org/data/definitions/${finding.cwe_id.replace("CWE-", "")}.html`}
                target="_blank"
                rel="noreferrer"
                className="mono"
                style={{ fontSize: 11, color: "var(--purple-mid)" }}
              >
                {finding.cwe_id}
              </a>
            )}
            {likelyFp && (
              <span style={{ fontSize: 10, color: "var(--amber)", fontWeight: 600 }}>Likely false positive</span>
            )}
            {finding.exploited_in_wild && (
              <span style={{ fontSize: 10, color: "var(--r-sec1)", fontWeight: 700 }}>Exploited in wild</span>
            )}
          </div>
          <p style={{ margin: "8px 0 4px", fontSize: 14, fontWeight: 600 }}>{findingDescription(finding)}</p>
          <p className="mono t-muted" style={{ fontSize: 12, margin: 0 }}>
            {finding.file_path}:{finding.line_start}
            {finding.tool || finding.rule_id ? ` · ${finding.tool ?? finding.rule_id}` : ""}
          </p>
        </div>
        <div style={{ textAlign: "right", minWidth: 100 }}>
          <div className="t-muted" style={{ fontSize: 10, marginBottom: 4 }}>
            Confidence
          </div>
          <div
            style={{
              height: 6,
              width: 80,
              background: "var(--bg-base)",
              borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${Math.round((finding.confidence ?? 0.5) * 100)}%`,
                background: severityColor(finding.severity ?? "LOW"),
              }}
            />
          </div>
          <div className="mono t-muted" style={{ fontSize: 10, marginTop: 4 }}>
            Blast {blastScore(finding)}
          </div>
        </div>
      </header>

      <button
        type="button"
        className="btn btn-ghost"
        style={{ marginTop: 10, fontSize: 12, padding: "4px 8px" }}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide details" : "Show attack path & remediation"}
      </button>

      {open && (
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 16 }}>
          <section>
            <div className="eyebrow">Attack path</div>
            <AttackPathVisualizer finding={finding} crownJewel={isCrown} />
          </section>

          <section>
            <div className="eyebrow">Blast radius</div>
            <p style={{ fontSize: 13, margin: "6px 0 0" }}>
              Reachable from: {(finding.reachable_from ?? []).join(", ") || "Unknown entry surface"}
            </p>
            {finding.ai_business_impact && (
              <p className="t-muted" style={{ fontSize: 12, marginTop: 6 }}>
                {finding.ai_business_impact}
              </p>
            )}
          </section>

          {finding.ai_attack_scenario && (
            <section>
              <div className="eyebrow">Attack scenario</div>
              <p style={{ fontSize: 13, margin: "6px 0 0" }}>{finding.ai_attack_scenario}</p>
            </section>
          )}

          <section>
            <div className="eyebrow">Remediation ({complexity.replace("-", " ")})</div>
            <ol style={{ margin: "8px 0 0", paddingLeft: 20, fontSize: 13 }}>
              {steps.map((step, i) => (
                <li key={i} style={{ marginBottom: 6 }}>
                  {step}
                </li>
              ))}
            </ol>
            {finding.ai_fix_code && (
              <pre
                style={{
                  marginTop: 10,
                  padding: 12,
                  fontSize: 11,
                  background: "var(--bg-base)",
                  borderRadius: 8,
                  overflow: "auto",
                }}
              >
                {finding.ai_fix_code}
              </pre>
            )}
          </section>

          {relatedGap && (
            <section>
              <div className="eyebrow">Compliance impact</div>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: relatedGap.status === "FAIL" ? "var(--r-sec1)" : "var(--green)",
                }}
              >
                {relatedGap.framework} {relatedGap.control} — {relatedGap.status ?? "NEEDS REVIEW"}
              </span>
            </section>
          )}
        </div>
      )}
    </article>
  );
}
