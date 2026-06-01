"use client";

type Props = {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
};

export function KpiSparkline({ data, color = "var(--purple-mid)", height = 28, width = 88 }: Props) {
  const points = data.length ? data : [0];
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = width / Math.max(points.length - 1, 1);

  const coords = points.map((v, i) => {
    const x = i * step;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const path = coords.length > 1 ? `M ${coords.join(" L ")}` : `M 0,${height / 2} L ${width},${height / 2}`;
  const area = `${path} L ${width},${height} L 0,${height} Z`;

  return (
    <svg
      className="kpi-sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden
    >
      <defs>
        <linearGradient id={`spark-${color.replace(/[^a-z0-9]/gi, "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.35} />
          <stop offset="100%" stopColor={color} stopOpacity={0.02} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#spark-${color.replace(/[^a-z0-9]/gi, "")})`} />
      <path d={path} fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
