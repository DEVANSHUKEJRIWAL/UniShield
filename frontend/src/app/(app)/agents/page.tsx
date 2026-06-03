"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
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
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { fetchAgentHealth } from "@/lib/api";
import { fetchWorkflowMetrics } from "@/lib/workflows-api";
import { features } from "@/lib/features";
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

const WORKFLOW_AGENT_NODE_MAP: Record<string, string> = {
  scr: "source-code-agent",
  cma: "compliance-agent",
  reporting: "reporting-agent",
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
        border: `1px solid ${a.status === "running" || a.status === "listening" ? "var(--green)" : "var(--border-default)"}`,
        borderRadius: 12,
        padding: 8,
        fontSize: 10,
        fontFamily: "IBM Plex Mono",
        boxShadow: a.status === "running" || a.status === "listening" ? "0 0 12px var(--violet-glow)" : undefined,
      },
    };
  });
  const edges: Edge[] = agents.filter((a) => a.id !== "orchestrator").map((a) => ({
    id: `e-${a.id}`,
    source: "orchestrator",
    target: a.id,
    animated: a.status === "running" || a.status === "listening",
    style: { stroke: a.status === "running" || a.status === "listening" ? "var(--violet-light)" : "var(--border-default)" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--violet)" },
  }));
  return { nodes, edges };
}

function mergeWorkflowStatuses(
  base: Record<string, string>,
  workflowAgents: Array<{ name: string; status: string }>,
  runningWorkflows: number
): Record<string, string> {
  const next = { ...base };
  if (runningWorkflows > 0) {
    next.orchestrator = "running";
  }
  for (const agent of workflowAgents) {
    const nodeId = WORKFLOW_AGENT_NODE_MAP[agent.name];
    if (nodeId) {
      next[nodeId] = agent.status;
    }
  }
  return next;
}

export default function AgentsPage() {
  const { token, tenantId, ready } = useAuth();
  const [statusMap, setStatusMap] = useState<Record<string, string>>({});
  const [workflowStats, setWorkflowStats] = useState({ running: 0, completed: 0, paused: 0 });
  const graph = useMemo(() => buildGraph(statusMap), [statusMap]);
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;

    const load = () => {
      if (features.orchestratorDashboardMetrics) {
        return fetchWorkflowMetrics(tenantId, token)
          .then((metrics) => {
            if (!metrics.available) throw new Error("orchestrator unavailable");
            const workflowAgents = metrics.agents ?? [];
            setWorkflowStats({
              running: metrics.running_workflows ?? 0,
              completed: metrics.completed_workflows ?? 0,
              paused: metrics.paused_workflows ?? 0,
            });
            setStatusMap(
              mergeWorkflowStatuses({}, workflowAgents, metrics.running_workflows ?? 0)
            );
          })
          .catch(() =>
            fetchAgentHealth(tenantId, token).then((d) => {
              const map: Record<string, string> = {};
              (d.agents ?? []).forEach((a: { name: string; status: string }) => {
                map[a.name] = a.status;
              });
              setStatusMap(map);
            })
          );
      }

      return fetchAgentHealth(tenantId, token).then((d) => {
        const map: Record<string, string> = {};
        (d.agents ?? []).forEach((a: { name: string; status: string }) => {
          map[a.name] = a.status;
        });
        setStatusMap(map);
      });
    };

    load().catch(() => {});
    const poll = features.orchestratorDashboardMetrics
      ? window.setInterval(() => {
          load().catch(() => {});
        }, 30000)
      : undefined;
    return () => {
      if (poll) window.clearInterval(poll);
    };
  }, [ready, token, tenantId]);

  const activeCount = Object.values(statusMap).filter((s) => s === "running" || s === "listening").length;
  const selectedMeta = selected ? AGENT_META[selected] : null;

  return (
    <>
      <AdminPageHeader
        title="AI Agents"
        subtitle={
          features.orchestratorUi
            ? `${activeCount} agents live · workflow orchestrator map · ${workflowStats.running} running`
            : `${activeCount} agents live · orchestrator neural network`
        }
      />

      <AnimatedCard className="h-[480px] overflow-hidden p-0">
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

      {selected && selectedMeta && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <AnimatedCard>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <h3 className="font-mono font-bold text-[var(--violet-light)]">
                  {selectedMeta.emoji} {selectedMeta.label}
                </h3>
                <p className="t-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  Status: <span className="mono">{statusMap[selected] ?? "idle"}</span>
                </p>
              </div>
              {features.orchestratorUi ? (
                <Link href="/workflows" className="btn-accent" style={{ textDecoration: "none" }}>
                  Open Security Workflows
                </Link>
              ) : null}
            </div>
            <p className="t-muted" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.5 }}>
              {features.orchestratorUi
                ? "Agent execution runs through the workflow orchestrator. Trigger Code Review and other playbooks from Security Workflows."
                : "Specialist agent node in the UniShield orchestrator topology."}
            </p>
            {features.orchestratorUi ? (
              <p className="mono t-muted" style={{ fontSize: 11, marginTop: 8 }}>
                {workflowStats.running} running · {workflowStats.completed} completed · {workflowStats.paused} paused
              </p>
            ) : null}
          </AnimatedCard>
        </motion.div>
      )}
    </>
  );
}
