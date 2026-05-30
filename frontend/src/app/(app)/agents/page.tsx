"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { agentRunStream } from "@/lib/api";

const AGENTS = [
  "orchestrator", "dark-web-agent", "source-code-agent", "insider-threat-agent",
  "threat-intel-agent", "vulnerability-agent", "incident-response-agent",
  "siem-analysis-agent", "network-security-agent", "compliance-agent",
  "forensics-agent", "graph-query-agent", "reporting-agent",
];

export default function AgentsPage() {
  const { tenantId } = useAuth();
  const [selected, setSelected] = useState("dark-web-agent");
  const [output, setOutput] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  const runAgent = async () => {
    setRunning(true);
    setOutput([]);
    const res = await agentRunStream(selected, tenantId ?? "meridian-financial", { query: "analyse latest threats" });
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) return;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value);
      text.split("\n").filter((l) => l.startsWith("data:")).forEach((l) => setOutput((p) => [...p, l.slice(5).trim()]));
    }
    setRunning(false);
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Agent Control</h1>
        <div className="mt-6 flex gap-4">
          <select value={selected} onChange={(e) => setSelected(e.target.value)} className="rounded border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2 text-sm">
            {AGENTS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <button onClick={runAgent} disabled={running} className="rounded bg-[var(--violet)] px-4 py-2 text-sm text-white disabled:opacity-50">
            {running ? "Running..." : "Run Analysis"}
          </button>
        </div>
        <div className="obsidian-card mono mt-6 max-h-96 overflow-y-auto text-xs">
          {output.length === 0 ? <p className="text-[var(--text-muted)]">Agent output will stream here via SSE</p> : output.map((l, i) => <p key={i} className="mb-1">{l}</p>)}
        </div>
      </main>
    </div>
  );
}
