"use client";

import { useCallback, useEffect, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, Node, Edge, useNodesState, useEdgesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/lib/auth";
import { fetchKgBlastRadius } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { RiskGauge } from "@/components/ui/RiskGauge";

const DEFAULT_ASSETS = [
  { id: "ws-42", label: "workstation-42", crown: false, risk: 65 },
  { id: "api-gw", label: "api-gateway", crown: false, risk: 45 },
  { id: "db-prod", label: "db-prod-01", crown: true, risk: 92 },
  { id: "auth", label: "auth-service", crown: false, risk: 55 },
];

function buildNetwork(assets: typeof DEFAULT_ASSETS, showAttack: boolean): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = assets.map((a, i) => ({
    id: a.id,
    position: { x: 100 + (i % 2) * 250, y: 80 + Math.floor(i / 2) * 150 },
    data: { label: a.label, crown: a.crown, risk: a.risk },
    style: {
      background: a.crown ? "linear-gradient(135deg, #f59e0b22, var(--bg-surface))" : "var(--bg-surface)",
      border: `2px solid ${a.crown ? "#f59e0b" : showAttack && a.id === "ws-42" ? "var(--red)" : "var(--border-default)"}`,
      borderRadius: a.crown ? 4 : 12,
      padding: 12,
      fontSize: 11,
      fontFamily: "IBM Plex Mono",
      boxShadow:
        showAttack && (a.id === "ws-42" || a.id === "db-prod")
          ? "0 0 16px var(--red-glow, var(--red-dim))"
          : undefined,
    },
  }));
  const edges: Edge[] = [
    {
      id: "e1",
      source: "ws-42",
      target: "api-gw",
      animated: showAttack,
      style: { stroke: showAttack ? "var(--red)" : "var(--border-default)" },
    },
    { id: "e2", source: "api-gw", target: "auth", style: { stroke: "var(--border-default)" } },
    {
      id: "e3",
      source: "api-gw",
      target: "db-prod",
      animated: showAttack,
      style: { stroke: showAttack ? "var(--red)" : "var(--amber)" },
    },
  ];
  return { nodes, edges };
}

export default function NetworkPage() {
  const { token, tenantId, ready } = useAuth();
  const [assets, setAssets] = useState(DEFAULT_ASSETS);
  const [showAttack, setShowAttack] = useState(false);
  const [selected, setSelected] = useState<(typeof DEFAULT_ASSETS)[0] | null>(null);
  const initial = buildNetwork(DEFAULT_ASSETS, false);
  const [nodes, , onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchKgBlastRadius("db-prod-01", tenantId, token)
      .then((d) => {
        const affected = d.affected_assets ?? [];
        if (affected.length) {
          const merged = [...DEFAULT_ASSETS];
          affected.forEach((id: string, i: number) => {
            if (!merged.find((a) => a.id === id)) {
              merged.push({ id, label: id, crown: id.includes("db"), risk: 70 + i * 3 });
            }
          });
          setAssets(merged);
          const g = buildNetwork(merged, showAttack);
          setEdges(g.edges);
        }
      })
      .catch(() => {});
  }, [ready, token, tenantId, showAttack, setEdges]);

  const toggleAttack = useCallback(() => {
    setShowAttack((s) => {
      const next = !s;
      const g = buildNetwork(assets, next);
      setEdges(g.edges);
      return next;
    });
  }, [setEdges, assets]);

  return (
    <>
      <AdminPageHeader
        title="Network"
        subtitle="Asset topology and blast-radius visualization"
        toolbar={
          <button type="button" onClick={toggleAttack} className="btn-accent" style={showAttack ? { background: "var(--red)" } : undefined}>
            {showAttack ? "Hide Attack Path" : "Show Attack Path"}
          </button>
        }
      />

      <AnimatedCard className="h-[420px] overflow-hidden p-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, n) => setSelected(assets.find((a) => a.id === n.id) ?? null)}
          fitView
          style={{ background: "var(--bg-primary)" }}
        >
          <Background gap={20} color="var(--border-subtle)" />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </AnimatedCard>

      <AnimatePresence>
        {selected && (
          <motion.div initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}>
            <AnimatedCard>
              <div className="flex items-center gap-6">
                <RiskGauge score={selected.risk} size="sm" />
                <div>
                  <h3 className="font-bold">{selected.label}</h3>
                  {selected.crown && <span className="font-mono text-xs text-[var(--amber)]">👑 Crown Jewel</span>}
                </div>
              </div>
            </AnimatedCard>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
