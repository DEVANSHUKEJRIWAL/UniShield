"use client";

export type VendorRisk = {
  name: string;
  score: number;
  issue: string;
  severity?: string;
};

type Props = {
  items: VendorRisk[];
  range: string;
};

export function VendorRiskCard({ items, range }: Props) {
  return (
    <div className="card">
      <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
        Vendor Risk · {range}
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {items.map((v) => (
          <li
            key={v.name}
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 8,
              padding: "8px 0",
              borderBottom: "1px solid var(--border-dim)",
              fontSize: 11,
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div className="t-title" style={{ fontSize: 12 }}>
                {v.name}
              </div>
              <div className="t-muted">{v.issue}</div>
            </div>
            <span
              className="mono"
              style={{
                fontWeight: 700,
                color: v.score >= 70 ? "var(--r-sec2)" : v.score >= 50 ? "var(--r-sec1)" : "var(--m3)",
              }}
            >
              {v.score}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
