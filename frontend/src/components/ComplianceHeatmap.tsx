interface Control {
  id: string;
  title: string;
  status: "implemented" | "partial" | "gap";
}

interface ComplianceHeatmapProps {
  framework: string;
  controls: Control[];
}

const STATUS_COLOURS = {
  implemented: "var(--success)",
  partial: "var(--warning)",
  gap: "var(--danger)",
} as const;

export function ComplianceHeatmap({ framework, controls }: ComplianceHeatmapProps) {
  return (
    <div className="obsidian-card">
      <h2 className="mb-4 text-lg font-semibold">{framework} Control Coverage</h2>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {controls.map((c) => (
          <div
            key={c.id}
            className="rounded border border-[var(--border)] p-3"
            style={{ borderLeftColor: STATUS_COLOURS[c.status], borderLeftWidth: 3 }}
          >
            <p className="mono text-xs font-medium">{c.id}</p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">{c.title}</p>
            <p className="mono mt-1 text-xs capitalize" style={{ color: STATUS_COLOURS[c.status] }}>
              {c.status}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
