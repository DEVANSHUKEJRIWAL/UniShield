"use client";

import { ThreatOriginMap } from "./ThreatOriginMap";

export type ThreatOrigin = {
  region: string;
  count: number;
  severity: string;
  source?: string;
  lat?: number;
  lng?: number;
  code?: string;
};

type Props = {
  items: ThreatOrigin[];
  range: string;
};

const SEV_COLOR: Record<string, string> = {
  critical: "var(--r-sec2)",
  high: "var(--r-sec1)",
  medium: "var(--r-sys)",
};

export function ThreatOriginCard({ items, range }: Props) {
  const max = Math.max(...items.map((i) => i.count), 1);

  return (
    <div className="card threat-origin-card">
      <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
        Threat Origin · {range}
      </div>
      <ThreatOriginMap items={items} />
      <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0 }}>
        {items.map((o) => (
          <li key={`${o.region}-${o.source ?? o.count}`} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
              <span className="t-title">
                {o.code ? <span className="mono" style={{ marginRight: 6, opacity: 0.7 }}>{o.code}</span> : null}
                {o.region}
              </span>
              <span className="mono" style={{ color: SEV_COLOR[o.severity] ?? "var(--text-muted)" }}>
                {o.count}
              </span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill ac-animate-width"
                style={{
                  width: `${(o.count / max) * 100}%`,
                  background: SEV_COLOR[o.severity] ?? "var(--purple-mid)",
                }}
              />
            </div>
            {o.source ? (
              <div className="mono t-muted" style={{ fontSize: 10, marginTop: 2 }}>
                {o.source}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
