"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import { GradientText } from "@/components/ui/primitives";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { agentRunStream, agentOrchestrateStream, fetchAgentHealth } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const AGENT_META: Record<string, { label: string; emoji: string }> = {
  orchestrator: { label: "Orchestrator", emoji: "🧠" },
  "dark-web-agent": { label: "Dark Web", emoji: "🕸️" },
  "source-code-agent": { label: "Source Code", emoji: "💻" },
  "insider-threat-agent": { label: "Insider Threat", emoji: "👤" },
  "threat-intel-agent": { label: "Threat Intel", emoji: "🎯" },
  "vulnerability-agent": { label: "Vulnerability", emoji: "🔓" },
  "incident-response-agent": { label: "Incident IR", emoji: "🚨" },
  "siem-analysis-agent": { label: "SIEM", emoji: "📊" },
  "network-security-agent": { label: "Network", emoji: "🌐" },
  "compliance-agent": { label: "Compliance", emoji: "📋" },
  "forensics-agent": { label: "Forensics", emoji: "🔬" },
  "graph-query-agent": { label: "Graph Query", emoji: "🔗" },
  "reporting-agent": { label: "Reporting", emoji: "📑" },
};

function buildGraph(statusMap: Record<string, string>): { nodes: Node[]; edges: Edge[] } {
  const agents = Object.entries(AGENT_META).map(([id, meta]) => ({
    id,
    ...meta,
    status: statusMap[id] ?? "idle",
  }));
  const nodes: Node[] = agents.map((a, i) => {
    if (a.id === "orchestrator") {
      return {
        id: a.id,
        position: { x: 400, y: 250 },
        data: { label: `${a.emoji} ${a.label}`, status: a.status },
        style: {
          background: "var(--bg-surface)",
          border: "2px solid var(--violet)",
          borderRadius: 16,
          padding: 12,
          fontSize: 12,
          fontFamily: "IBM Plex Mono",
          boxShadow: "0 0 24px var(--violet-glow)",
          minWidth: 140,
        },
      };
    }
    const angle = ((i - 1) / (agents.length - 1)) * Math.PI * 2;
    const r = 220;
    return {
      id: a.id,
      position: { x: 400 + Math.cos(angle) * r, y: 250 + Math.sin(angle) * r },
      data: { label: `${a.emoji} ${a.label}`, status: a.status },
      style: {
        background: "var(--bg-surface)",
        border: `1px solid ${a.status === "running" ? "var(--green)" : "var(--border-default)"}`,
        borderRadius: 12,
        padding: 8,
        fontSize: 10,
        fontFamily: "IBM Plex Mono",
        boxShadow: a.status === "running" ? "0 0 12px var(--violet-glow)" : undefined,
      },
    };
  });
  const edges: Edge[] = agents.filter((a) => a.id !== "orchestrator").map((a) => ({
    id: `e-${a.id}`,
    source: "orchestrator",
    target: a.id,
    animated: a.status === "running",
    style: { stroke: a.status === "running" ? "var(--violet-light)" : "var(--border-default)" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--violet)" },
  }));
  return { nodes, edges };
}

export default function AgentsPage() {
  const { token, tenantId, ready } = useAuth();
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const graph = useMemo(() => buildGraph(statusMap), [statusMap]);
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);
  const [selected, setSelected] = useState<string | null>(null);
  const [output, setOutput] = useState<string[]>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchAgentHealth(tenantId, token).then((d) => {
      const map: Record<string, string> = {};
      (d.agents ?? []).forEach((a: { name: string; status: string }) => {
        map[a.name] = a.status;
      });
      setStatusMap(map);
    }).catch(() => {});
  }, [ready, token, tenantId]);

  const runAgent = useCallback(async (name: string) => {
    setRunning(true);
    setOutput([]);
    const res = await agentRunStream(name, tenantId ?? "meridian-financial", { query: "analyse" });
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) return;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      decoder.decode(value).split("\n").filter((l) => l.startsWith("data:")).forEach((l) => setOutput((p) => [...p, l.slice(5).trim()]));
    }
    setRunning(false);
  }, [tenantId]);

  const runOrchestrator = useCallback(async () => {
    setRunning(true);
    setOutput([]);
    const res = await agentOrchestrateStream(tenantId ?? "meridian-financial", {
      type: "credential_leak",
      domain: "meridian.com",
      severity: "critical",
    });
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) return;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      decoder.decode(value).split("\n").filter((l) => l.startsWith("data:")).forEach((l) => setOutput((p) => [...p, l.slice(5).trim()]));
    }
    setRunning(false);
  }, [tenantId]);

  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="text-3xl font-extrabold">
        <GradientText>AGENT NEURAL NETWORK</GradientText>
      </motion.h1>

      <AnimatedCard className="h-[480px] p-0 overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, n) => setSelected(n.id)}
          fitView
          style={{ background: "var(--bg-primary)" }}
        >
          <Background color="var(--violet)" gap={24} size={1} />
          <Controls />
          <MiniMap nodeColor={() => "var(--violet)"} maskColor="var(--bg-primary)" />
        </ReactFlow>
      </AnimatedCard>

      {selected && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <AnimatedCard>
            <div className="flex items-center justify-between">
              <h3 className="font-mono font-bold text-[var(--violet-light)]">{selected}</h3>
              <motion.button
                whileTap={{ scale: 0.95 }}
                whileHover={{ scale: 1.05 }}
                disabled={running}
                onClick={() => (selected === "orchestrator" ? runOrchestrator() : runAgent(selected))}
                className="rounded-xl px-4 py-2 text-sm font-bold text-white"
                style={{ background: "linear-gradient(135deg, var(--violet), var(--magenta))" }}
              >
                {running ? "REASONING..." : selected === "orchestrator" ? "Run Workflow" : "Run Agent"}
              </motion.button>
            </div>
            <div className="mt-4 max-h-40 overflow-y-auto font-mono text-xs text-[var(--text-secondary)]">
              {output.map((l, i) => (
                <p key={i}>{l}</p>
              ))}
            </div>
          </AnimatedCard>
        </motion.div>
      )}
    </div>
  );
}
