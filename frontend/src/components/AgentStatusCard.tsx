interface AgentHealth {
  name: string;
  status: "idle" | "running" | "error";
  healthy: boolean;
  lastRun?: string;
}

interface AgentStatusCardProps {
  agent: AgentHealth;
}

const STATUS_COLOURS = {
  idle: "var(--text-muted)",
  running: "var(--cyan)",
  error: "var(--danger)",
} as const;

export function AgentStatusCard({ agent }: AgentStatusCardProps) {
  return (
    <div className="obsidian-card flex items-center justify-between">
      <div>
        <p className="mono text-sm font-medium">{agent.name}</p>
        <p
          className="mono mt-1 text-xs capitalize"
          style={{ color: STATUS_COLOURS[agent.status] }}
        >
          {agent.status}
        </p>
      </div>
      <div
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: agent.healthy ? "var(--success)" : "var(--danger)" }}
      />
    </div>
  );
}
