"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/lib/auth";
import { fetchDashboard, fetchAlerts, fetchAgentHealth, agentWsUrl } from "@/lib/api";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { AgentStatusDot } from "@/components/ui/primitives";
import { useWebSocket } from "@/hooks/useWebSocket";

const AGENT_ICONS: Record<string, string> = {
  orchestrator: "🧠",
  "dark-web-agent": "🕸️",
  "source-code-agent": "💻",
  "insider-threat-agent": "👤",
  "threat-intel-agent": "🎯",
  "vulnerability-agent": "🔓",
  "incident-response-agent": "🚨",
  "siem-analysis-agent": "📊",
  "network-security-agent": "🌐",
  "compliance-agent": "📋",
  "forensics-agent": "🔬",
  "graph-query-agent": "🔗",
  "reporting-agent": "📑",
};

const TREND_FALLBACK = [
  { d: "W1", v: 45 },
  { d: "W2", v: 52 },
  { d: "W3", v: 48 },
  { d: "W4", v: 61 },
  { d: "W5", v: 58 },
  { d: "W6", v: 72 },
];

export default function DashboardPage() {
  const { token, tenantId, ready } = useAuth();
  const [threatScore, setThreatScore] = useState(72);
  const [kpis, setKpis] = useState({ alerts: 0, findings: 0, agents: 0, hitl: 0, critical: 0 });
  const [trend, setTrend] = useState(TREND_FALLBACK);
  const [events, setEvents] = useState<Array<{ id: string; severity: "critical" | "high" | "medium" | "low" | "info"; message: string; time: string; source: string }>>([]);
  const [agents, setAgents] = useState<Array<{ name: string; status: "running" | "idle" | "error" }>>([]);
  const eventKeyRef = useRef(0);

  useWebSocket(tenantId ? agentWsUrl(tenantId) : null, {
    onMessage: (data) => {
      const msg = data as {
        agent?: string;
        finding?: { finding_id?: string; title?: string; severity?: string; tenant_id?: string };
      };
      const finding = msg.finding;
      if (!finding?.title) return;
      eventKeyRef.current += 1;
      const findingId = finding.finding_id;
      setEvents((prev) => [
        {
          id: findingId ?? `${msg.agent ?? "agent"}-${Date.now()}-${eventKeyRef.current}`,
          severity: (finding.severity ?? "medium") as "critical" | "high" | "medium" | "low" | "info",
          message: finding.title ?? "Agent finding",
          time: new Date().toLocaleTimeString(),
          source: msg.agent ?? "agent",
        },
        ...prev,
      ].slice(0, 8));
    },
  });

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    fetchDashboard(tenantId, token).then((d) => {
      const score = Math.round((d.kpis?.risk_score ?? 0.72) * 100);
      setThreatScore(score);
      setKpis({
        alerts: d.kpis?.active_alerts ?? 0,
        findings: d.kpis?.total_findings ?? 0,
        agents: d.agents_active ?? 0,
        hitl: d.hitl_queue_depth ?? 0,
        critical: d.kpis?.critical_findings ?? 0,
      });
      if (d.risk_trend?.length) {
        setTrend(d.risk_trend.map((p: { label: string; score: number }) => ({ d: p.label, v: p.score })));
      }
    }).catch(() => {});
    fetchAlerts(tenantId, token).then((alerts) => {
      setEvents(
        alerts.slice(0, 8).map((a: { id: string; severity: string; title: string; source: string; created_at: string }) => ({
          id: a.id,
          severity: a.severity as "critical" | "high" | "medium" | "low" | "info",
          message: a.title,
          time: new Date(a.created_at).toLocaleTimeString(),
          source: a.source,
        }))
      );
    }).catch(() => {});
    fetchAgentHealth(tenantId, token)
      .then((d) =>
        setAgents(
          (d.agents ?? []).map((a: { name: string; status: string }) => ({
            name: a.name,
            status: (a.status === "running" ? "running" : a.status === "error" ? "error" : "idle") as "running" | "idle" | "error",
          }))
        )
      )
      .catch(() => setAgents([
        { name: "orchestrator", status: "running" },
        { name: "dark-web-agent", status: "running" },
        { name: "threat-intel-agent", status: "idle" },
      ]));
  }, [ready, token, tenantId]);

  const threatColor = threatScore > 60 ? "var(--red)" : threatScore > 30 ? "var(--amber)" : "var(--green)";

  return (
    <div className="space-y-6">
      {/* Threat Level Hero */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl border p-8 scan-overlay"
        style={{
          borderColor: threatColor,
          background: `linear-gradient(135deg, color-mix(in srgb, ${threatColor} 12%, var(--bg-surface)), var(--bg-surface))`,
          boxShadow: `0 0 40px color-mix(in srgb, ${threatColor} 25%, transparent)`,
        }}
      >
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[var(--text-muted)]">Platform Threat Level</p>
        <div className="mt-2 flex items-end gap-4">
          <span className="text-[80px] font-extrabold leading-none" style={{ fontFamily: "var(--font-display)", color: threatColor }}>
            <CountUp end={threatScore} duration={2} />
          </span>
          <span className="mb-4 text-2xl text-[var(--text-muted)]">/100</span>
        </div>
        <motion.div
          className="absolute inset-0 pointer-events-none"
          animate={{ opacity: [0.03, 0.08, 0.03] }}
          transition={{ repeat: Infinity, duration: 3 }}
          style={{ background: `linear-gradient(90deg, transparent, ${threatColor}, transparent)` }}
        />
      </motion.div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {[
          { label: "Active Alerts", value: kpis.alerts, pulse: kpis.alerts > 10 },
          { label: "Findings", value: kpis.findings },
          { label: "Critical", value: kpis.critical, pulse: true },
          { label: "Agents Live", value: kpis.agents },
          { label: "HITL Queue", value: kpis.hitl },
        ].map((k, i) => (
          <AnimatedCard key={k.label} delay={i * 0.08} float className={k.pulse ? "animate-glow-pulse" : ""}>
            <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">{k.label}</p>
            <p className="mt-2 text-3xl font-bold text-[var(--violet-light)]">
              <AnimatedNumber value={k.value} />
            </p>
          </AnimatedCard>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Threat Feed */}
        <AnimatedCard delay={0.2} className="relative lg:col-span-2 scan-overlay overflow-hidden">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold" style={{ fontFamily: "var(--font-display)" }}>Live Threat Feed</h2>
            <motion.span
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="font-mono text-[10px] text-[var(--green)]"
            >
              ● LIVE
            </motion.span>
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto font-mono text-xs">
            {(events.length ? events : [{ id: "0", severity: "info" as const, message: "Awaiting live events...", time: "now", source: "system" }]).map((e, i) => (
              <motion.div
                key={e.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] p-3"
                style={{ borderLeftWidth: 4, borderLeftColor: e.severity === "critical" ? "var(--red)" : e.severity === "high" ? "var(--amber)" : "var(--violet)" }}
              >
                <SeverityBadge severity={e.severity} />
                <div>
                  <p className="text-[var(--text-primary)]">{e.message}</p>
                  <p className="mt-1 text-[var(--text-muted)]">{e.source} · {e.time}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </AnimatedCard>

        {/* Agent Grid */}
        <AnimatedCard delay={0.3}>
          <h2 className="mb-4 text-lg font-bold" style={{ fontFamily: "var(--font-display)" }}>Agent Status</h2>
          <div className="grid grid-cols-1 gap-2">
            {(agents.length ? agents : [{ name: "orchestrator", status: "running" as const }]).slice(0, 8).map((a, i) => (
              <motion.div
                key={a.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ scale: 1.02 }}
                className="flex items-center gap-3 rounded-xl border border-[var(--border-subtle)] p-2"
                style={a.status === "running" ? { boxShadow: "0 0 12px var(--violet-glow)" } : {}}
              >
                <span className="text-lg">{AGENT_ICONS[a.name] ?? "🤖"}</span>
                <div className="flex-1 truncate font-mono text-[11px]">{a.name}</div>
                <AgentStatusDot status={a.status} />
              </motion.div>
            ))}
          </div>
        </AnimatedCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AnimatedCard delay={0.4}>
          <h2 className="mb-4 font-bold" style={{ fontFamily: "var(--font-display)" }}>Risk Trend (30d)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trend}>
              <defs>
                <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--violet)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="var(--violet)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="d" stroke="var(--text-muted)" fontSize={10} />
              <YAxis stroke="var(--text-muted)" fontSize={10} />
              <Tooltip contentStyle={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)" }} />
              <Area type="monotone" dataKey="v" stroke="var(--violet-light)" fill="url(#riskGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </AnimatedCard>

        <AnimatedCard delay={0.5}>
          <h2 className="mb-4 font-bold" style={{ fontFamily: "var(--font-display)" }}>Top Active Alerts</h2>
          <div className="space-y-2">
            {events.slice(0, 5).map((e) => (
              <div key={e.id} className="flex items-center justify-between rounded-lg bg-[var(--bg-tertiary)] p-3">
                <span className="truncate text-sm">{e.message}</span>
                <SeverityBadge severity={e.severity} />
              </div>
            ))}
          </div>
        </AnimatedCard>
      </div>
    </div>
  );
}
