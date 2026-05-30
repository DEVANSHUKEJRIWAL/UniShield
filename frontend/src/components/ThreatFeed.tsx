interface ThreatEvent {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  message: string;
  timestamp: string;
  source: string;
}

interface ThreatFeedProps {
  events: ThreatEvent[];
  liveStream?: boolean;
}

const SEVERITY_COLOURS = {
  critical: "var(--danger)",
  high: "var(--warning)",
  medium: "var(--magenta)",
  low: "var(--cyan)",
  info: "var(--text-muted)",
} as const;

export function ThreatFeed({ events, liveStream }: ThreatFeedProps) {
  return (
    <div className="obsidian-card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Threat Feed</h2>
        {liveStream && (
          <span className="mono flex items-center gap-2 text-xs text-[var(--success)]">
            <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--success)]" />
            LIVE
          </span>
        )}
      </div>
      <div className="max-h-80 space-y-2 overflow-y-auto">
        {events.map((event) => (
          <div
            key={event.id}
            className="flex items-start gap-3 rounded border border-[var(--border)] bg-[var(--bg-surface)] p-3"
          >
            <span
              className="mono mt-0.5 text-xs font-medium uppercase"
              style={{ color: SEVERITY_COLOURS[event.severity] }}
            >
              {event.severity}
            </span>
            <div className="flex-1">
              <p className="text-sm">{event.message}</p>
              <p className="mono mt-1 text-xs text-[var(--text-muted)]">
                {event.source} · {event.timestamp}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
