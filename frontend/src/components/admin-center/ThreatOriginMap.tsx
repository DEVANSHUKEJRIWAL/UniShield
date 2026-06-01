"use client";

import type { ThreatOrigin } from "./ThreatOriginCard";

type Props = {
  items: ThreatOrigin[];
};

function project(lat: number, lng: number, w: number, h: number) {
  const x = ((lng + 180) / 360) * w;
  const y = ((90 - lat) / 180) * h;
  return { x, y };
}

const SEV_COLOR: Record<string, string> = {
  critical: "var(--r-sec2)",
  high: "var(--r-sec1)",
  medium: "var(--r-sys)",
};

export function ThreatOriginMap({ items }: Props) {
  const w = 320;
  const h = 140;

  return (
    <div className="threat-geo-map" aria-label="Threat origin map">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img">
        <rect x={0} y={0} width={w} height={h} rx={12} fill="var(--surface-raised)" />
        {[0.25, 0.5, 0.75].map((p) => (
          <line
            key={`lat-${p}`}
            x1={0}
            x2={w}
            y1={h * p}
            y2={h * p}
            stroke="var(--border-dim)"
            strokeWidth={0.5}
            opacity={0.6}
          />
        ))}
        {[0.25, 0.5, 0.75].map((p) => (
          <line
            key={`lng-${p}`}
            x1={w * p}
            x2={w * p}
            y1={0}
            y2={h}
            stroke="var(--border-dim)"
            strokeWidth={0.5}
            opacity={0.6}
          />
        ))}
        {items.map((o) => {
          const lat = o.lat ?? 20;
          const lng = o.lng ?? 0;
          const { x, y } = project(lat, lng, w, h);
          const r = 4 + Math.min(o.count, 8);
          const color = SEV_COLOR[o.severity] ?? "var(--purple-mid)";
          return (
            <g key={`${o.region}-${o.source ?? o.count}`}>
              <circle cx={x} cy={y} r={r + 4} fill={color} opacity={0.18} className="geo-pulse" />
              <circle cx={x} cy={y} r={r} fill={color} opacity={0.85} />
              <title>{`${o.region}: ${o.count} (${o.severity})`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
