interface KPIStripProps {
  metrics: Array<{ label: string; value: string | number; trend?: string }>;
}

export function KPIStrip({ metrics }: KPIStripProps) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {metrics.map((metric) => (
        <div key={metric.label} className="obsidian-card">
          <p className="mono text-xs uppercase tracking-wider text-[var(--text-muted)]">
            {metric.label}
          </p>
          <p className="kpi-value mt-1 text-[var(--violet)]">{metric.value}</p>
          {metric.trend && (
            <p className="mono mt-1 text-xs text-[var(--text-secondary)]">{metric.trend}</p>
          )}
        </div>
      ))}
    </div>
  );
}
