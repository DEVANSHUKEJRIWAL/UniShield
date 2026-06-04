"use client";

import type { ScrFinding } from "@/lib/scr-parse";

type Props = {
  finding: ScrFinding;
  crownJewel?: boolean;
};

export function AttackPathVisualizer({ finding, crownJewel }: Props) {
  const entry = finding.reachable_from?.[0] ?? "Entry point";
  const hops = finding.data_flow ?? [];
  const sink = finding.file_path
    ? `${finding.file_path.split("/").pop()}:${finding.line_start ?? "?"}`
    : "Sink";

  const nodes = [entry, ...hops.filter((h) => h !== entry), sink];
  const colors = ["#22c55e", "#eab308", "#f97316", "#ef4444"];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        flexWrap: "wrap",
        padding: crownJewel ? "10px 12px" : 0,
        border: crownJewel ? "2px solid var(--r-sec1)" : undefined,
        borderRadius: 8,
      }}
    >
      {crownJewel && (
        <span title="Crown jewel path" style={{ fontSize: 16, marginRight: 4 }}>
          👑
        </span>
      )}
      {nodes.map((label, i) => (
        <div key={`${label}-${i}`} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              padding: "6px 10px",
              borderRadius: 8,
              fontSize: 11,
              fontWeight: 600,
              background: `${colors[Math.min(i, colors.length - 1)]}22`,
              border: `1px solid ${colors[Math.min(i, colors.length - 1)]}`,
              color: "var(--text-primary)",
              maxWidth: 140,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={label}
          >
            {label}
          </div>
          {i < nodes.length - 1 && (
            <span style={{ color: "var(--m3)", fontSize: 12 }}>→</span>
          )}
        </div>
      ))}
    </div>
  );
}
