import { Sidebar } from "@/components/Sidebar";
import { KPIStrip } from "@/components/KPIStrip";
import { ThreatFeed } from "@/components/ThreatFeed";
import { AgentStatusCard } from "@/components/AgentStatusCard";

const MOCK_KPIS = [
  { label: "Active Alerts", value: 23, trend: "+3 today" },
  { label: "Risk Score", value: "72", trend: "High" },
  { label: "Agents Running", value: "4/13", trend: "Healthy" },
  { label: "HITL Queue", value: 2, trend: "1 P0 pending" },
];

const MOCK_EVENTS = [
  {
    id: "1",
    severity: "critical" as const,
    message: "Credential exposure detected on dark web forum",
    timestamp: "2 min ago",
    source: "dark-web-agent",
  },
  {
    id: "2",
    severity: "high" as const,
    message: "Anomalous login pattern for privileged user",
    timestamp: "8 min ago",
    source: "insider-threat-agent",
  },
  {
    id: "3",
    severity: "medium" as const,
    message: "CVE-2024-1234 affects 3 crown-jewel services",
    timestamp: "15 min ago",
    source: "vulnerability-agent",
  },
];

const MOCK_AGENTS = [
  { name: "orchestrator", status: "running" as const, healthy: true },
  { name: "dark-web-agent", status: "running" as const, healthy: true },
  { name: "threat-intel-agent", status: "idle" as const, healthy: true },
  { name: "compliance-agent", status: "idle" as const, healthy: true },
];

export default function DashboardPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <header className="mb-8">
          <h1 className="text-2xl font-bold">SOC Dashboard</h1>
          <p className="mt-1 text-[var(--text-secondary)]">
            Meridian Financial Group — live threat monitoring
          </p>
        </header>

        <section className="mb-8">
          <KPIStrip metrics={MOCK_KPIS} />
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ThreatFeed events={MOCK_EVENTS} liveStream />
          </div>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Agent Status</h2>
            {MOCK_AGENTS.map((agent) => (
              <AgentStatusCard key={agent.name} agent={agent} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
