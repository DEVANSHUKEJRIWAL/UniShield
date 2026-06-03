"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search } from "lucide-react";
import { toast } from "sonner";
import { useAdminDashboard, type AlertEvent } from "@/hooks/useAdminDashboard";
import { ThreatStrip } from "@/components/admin-center/ThreatStrip";
import { AdminKpiStrip } from "@/components/admin-center/AdminKpiStrip";
import { AIBriefCard } from "@/components/admin-center/AIBriefCard";
import { ThreatActivityCard } from "@/components/admin-center/ThreatActivityCard";
import { PriorityQueue } from "@/components/admin-center/PriorityQueue";
import { EnvRiskCard } from "@/components/admin-center/EnvRiskCard";
import { VendorRiskCard } from "@/components/admin-center/VendorRiskCard";
import { ThreatOriginCard } from "@/components/admin-center/ThreatOriginCard";
import { BusinessImpactCard } from "@/components/admin-center/BusinessImpactCard";
import { IncidentModal } from "@/components/admin-center/IncidentModal";
import { useAuth } from "@/lib/auth";
import { searchDashboard } from "@/lib/api";
import { features } from "@/lib/features";

type Range = "24h" | "7d" | "30d";

export default function DashboardPage() {
  const router = useRouter();
  const { token, tenantId } = useAuth();
  const [range, setRange] = useState<Range>("7d");
  const [search, setSearch] = useState("");
  const [searchBusy, setSearchBusy] = useState(false);
  const [incident, setIncident] = useState<AlertEvent | null>(null);
  const {
    kpis,
    trend,
    sparklines,
    alerts,
    criticalSummary,
    vendorRisks,
    threatOrigins,
    aiBrief,
    updatedAt,
    metricsSource,
    severityMix,
    workflowStats,
    refresh,
  } = useAdminDashboard(range);

  const severityBar = [
    { key: "critical", color: "var(--purple-deep)", pct: severityMix.critical },
    { key: "high", color: "var(--m3)", pct: severityMix.high },
    { key: "medium", color: "var(--lavender)", pct: severityMix.medium },
    { key: "low", color: "var(--progress-track)", pct: severityMix.low },
  ];
  const severityTotal = severityBar.reduce((sum, row) => sum + row.pct, 0);
  const normalizedSeverityBar =
    severityTotal > 0
      ? severityBar
      : [
          { key: "critical", color: "var(--purple-deep)", pct: 38 },
          { key: "high", color: "var(--m3)", pct: 25 },
          { key: "medium", color: "var(--lavender)", pct: 18 },
          { key: "low", color: "var(--progress-track)", pct: 19 },
        ];
  const updatedLabel = updatedAt
    ? `Updated ${updatedAt.toLocaleTimeString()} · ${range}`
    : `Updated just now · ${range}`;

  const threatLevel =
    kpis.riskScore >= 70 ? "ELEVATED" : kpis.riskScore >= 50 ? "MODERATE" : "LOW";
  const threatColor =
    kpis.riskScore >= 70 ? "var(--r-sec1)" : kpis.riskScore >= 50 ? "var(--r-sec1)" : "var(--m3)";

  const handleSearch = async () => {
    const q = search.trim();
    if (!q) return;
    if (!token || !tenantId) {
      router.push("/alerts");
      return;
    }
    setSearchBusy(true);
    try {
      const data = await searchDashboard(tenantId, token, q);
      const entity = data.entity;
      const top = data.results?.[0];
      if (top?.route) {
        const path = top.id ? `${top.route}?q=${encodeURIComponent(q)}&id=${top.id}` : `${entity.route}?q=${encodeURIComponent(q)}`;
        toast.message(`${entity.label} match`, { description: top.title ?? q });
        router.push(path);
        return;
      }
      router.push(`${entity.route}?q=${encodeURIComponent(q)}`);
    } catch {
      router.push(`/alerts?q=${encodeURIComponent(q)}`);
    } finally {
      setSearchBusy(false);
    }
  };

  const handleDrill = (key: string) => {
    if (key === "findings" && features.orchestratorUi && metricsSource === "orchestrator") {
      router.push("/workflows");
    } else if (key === "risk" || key === "findings") {
      document.getElementById("envRiskCard")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else if (key === "critical" || key === "hitl") {
      router.push("/investigation?tab=hitl");
    } else if (key === "agents") {
      router.push(features.orchestratorUi ? "/workflows" : "/agents");
    } else if (key === "compliance") {
      router.push("/compliance");
    }
  };

  return (
    <>
      <ThreatStrip alerts={alerts} onSelect={() => router.push("/alerts")} />

      <div className="dash-header ac-fade-up" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 className="t-title">Admin Center</h1>
          <p className="t-muted" style={{ margin: 0, fontSize: 13 }}>
            {tenantId ?? "Tenant"} ·{" "}
            {metricsSource === "orchestrator" ? (
              <>
                <span className="mono">SCR Workflows</span>
                {features.orchestratorUi ? (
                  <>
                    {" "}
                    ·{" "}
                    <button
                      type="button"
                      style={{
                        fontSize: 13,
                        padding: 0,
                        border: "none",
                        background: "none",
                        color: "var(--lavender)",
                        cursor: "pointer",
                        textDecoration: "underline",
                      }}
                      onClick={() => router.push("/workflows")}
                    >
                      View runs
                    </button>
                  </>
                ) : null}
              </>
            ) : (
              <span className="mono">Live</span>
            )}{" "}
            · Threat:{" "}
            <span style={{ color: threatColor, fontWeight: 700 }}>{threatLevel}</span>
          </p>
        </div>
        <div className="dash-toolbar">
          <div style={{ position: "relative" }}>
            <Search
              style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", width: 14, height: 14, color: "var(--lavender)" }}
            />
            <input
              type="search"
              className="search-input"
              placeholder="CVE, host, IP, agent…"
              aria-label="Search dashboard"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <button type="button" className="btn-ghost" onClick={() => router.push("/investigation?tab=hitl")}>
            View Active Incidents <span className="mono">({kpis.hitlQueue || kpis.activeAlerts})</span>
          </button>
          <button type="button" className="btn-ghost" onClick={() => router.push("/reporting")}>
            Export
          </button>
          <button
            type="button"
            className="btn-accent"
            disabled={searchBusy}
            onClick={() => document.getElementById("aiBriefCard")?.scrollIntoView({ behavior: "smooth" })}
          >
            AI Summary
          </button>
        </div>
      </div>

      <AdminKpiStrip
        kpis={kpis}
        sparklines={sparklines}
        range={range}
        onRangeChange={setRange}
        updatedLabel={updatedLabel}
        onDrill={handleDrill}
        dataSource={metricsSource}
      />

      <div className="content-grid ac-stagger-in">
        <div className="main-col">
          <div className="left-col">
            <div id="aiBriefCard">
              <AIBriefCard
                kpis={kpis}
                alerts={alerts}
                criticalSummary={criticalSummary}
                aiBrief={aiBrief}
                metricsSource={metricsSource}
              />
            </div>
            <ThreatActivityCard alerts={alerts} trend={trend} />

            <div className="sub-grid-2">
              <VendorRiskCard items={vendorRisks} range={range} />
              <ThreatOriginCard items={threatOrigins} range={range} />
            </div>

            <div className="sub-grid-2">
              <BusinessImpactCard kpis={kpis} range={range} />

              <div className="card">
                <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
                  Agent Health · {metricsSource === "orchestrator" ? "workflows" : "live"}
                </div>
                <p className="t-muted" style={{ fontSize: 11, marginBottom: 10 }}>
                  {kpis.agentsActive} of {kpis.agentsTotal || kpis.agentsActive} workflow agents active
                  {metricsSource === "orchestrator"
                    ? ` · ${workflowStats.running} running · ${workflowStats.completed} completed`
                    : null}
                </p>
                <div className="progress-track" style={{ height: 6, marginBottom: 12 }}>
                  <div
                    className="progress-fill ac-animate-width"
                    style={{
                      width: `${kpis.agentsTotal ? (kpis.agentsActive / kpis.agentsTotal) * 100 : 100}%`,
                      background: "var(--m3)",
                    }}
                  />
                </div>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => router.push(features.orchestratorUi ? "/workflows" : "/agents")}
                >
                  {features.orchestratorUi ? "Open security workflows →" : "Open agent console →"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="right-col">
          <PriorityQueue alerts={alerts} onSelect={setIncident} />
          <div id="envRiskCard">
            <EnvRiskCard kpis={kpis} />
          </div>

          <div className="card">
            <div className="t-title" style={{ fontSize: 13, marginBottom: 4 }}>
              SLA &amp; Engagement
            </div>
            <div className="t-muted" style={{ fontSize: 11, marginBottom: 6 }}>
              Severity mix · {metricsSource === "orchestrator" ? "SCR workflows" : "30d"}
            </div>
            <div style={{ display: "flex", height: 6, borderRadius: 999, overflow: "hidden" }}>
              {normalizedSeverityBar.map((row) => (
                <span key={row.key} style={{ width: `${row.pct}%`, background: row.color }} />
              ))}
            </div>
            {[
              {
                label: metricsSource === "orchestrator" ? "Open findings" : "Alert SLA",
                val: metricsSource === "orchestrator" ? String(kpis.activeAlerts) : kpis.activeAlerts === 0 ? "100%" : "98.2%",
                color: "var(--m3)",
              },
              {
                label: "Agents online",
                val: `${kpis.agentsActive}/${kpis.agentsTotal || "—"}`,
                color: "var(--m3)",
              },
              {
                label: metricsSource === "orchestrator" ? "Paused workflows" : "HITL backlog",
                val: String(kpis.hitlQueue),
                color: kpis.hitlQueue > 0 ? "var(--r-sec1)" : "var(--m3)",
              },
            ].map((row) => (
              <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", fontSize: 11, borderTop: "1px solid var(--border-dim)" }}>
                <span className="t-muted">{row.label}</span>
                <span className="mono" style={{ color: row.color, fontWeight: 600 }}>
                  {row.val}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <IncidentModal alert={incident} onClose={() => setIncident(null)} onUpdated={refresh} />
    </>
  );
}
