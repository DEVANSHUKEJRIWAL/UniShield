"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search } from "lucide-react";
import { useAdminDashboard, type AlertEvent } from "@/hooks/useAdminDashboard";
import { ThreatStrip } from "@/components/admin-center/ThreatStrip";
import { AdminKpiStrip } from "@/components/admin-center/AdminKpiStrip";
import { AIBriefCard } from "@/components/admin-center/AIBriefCard";
import { ThreatActivityCard } from "@/components/admin-center/ThreatActivityCard";
import { PriorityQueue } from "@/components/admin-center/PriorityQueue";
import { EnvRiskCard } from "@/components/admin-center/EnvRiskCard";
import { VendorRiskCard } from "@/components/admin-center/VendorRiskCard";
import { ThreatOriginCard } from "@/components/admin-center/ThreatOriginCard";
import { IncidentModal } from "@/components/admin-center/IncidentModal";

type Range = "24h" | "7d" | "30d";

export default function DashboardPage() {
  const router = useRouter();
  const [range, setRange] = useState<Range>("7d");
  const [search, setSearch] = useState("");
  const [incident, setIncident] = useState<AlertEvent | null>(null);
  const { kpis, trend, alerts, criticalSummary, vendorRisks, threatOrigins, updatedAt, tenantId } =
    useAdminDashboard(range);

  const updatedLabel = updatedAt
    ? `Updated ${updatedAt.toLocaleTimeString()} · ${range}`
    : `Updated just now · ${range}`;

  const threatLevel =
    kpis.riskScore >= 70 ? "ELEVATED" : kpis.riskScore >= 50 ? "MODERATE" : "LOW";
  const threatColor =
    kpis.riskScore >= 70 ? "var(--r-sec1)" : kpis.riskScore >= 50 ? "var(--r-sec1)" : "var(--m3)";

  const handleSearch = () => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    if (/agent|bot/.test(q)) router.push("/agents");
    else if (/compliance|pci|soc/.test(q)) router.push("/compliance");
    else if (/hitl|gate|investigation/.test(q)) router.push("/investigation");
    else router.push("/alerts");
  };

  const handleDrill = (key: string) => {
    if (key === "risk" || key === "findings") {
      document.getElementById("envRiskCard")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else if (key === "critical" || key === "hitl") {
      router.push("/investigation");
    } else if (key === "agents") {
      router.push("/agents");
    } else if (key === "compliance") {
      router.push("/compliance");
    }
  };

  return (
    <>
      <ThreatStrip alerts={alerts} onSelect={() => router.push("/alerts")} />

      <div className="dash-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 20 }}>
        <div>
          <h1 className="t-title">Admin Center</h1>
          <p className="t-muted" style={{ margin: 0, fontSize: 13 }}>
            {tenantId ?? "Tenant"} · <span className="mono">Live</span> · Threat:{" "}
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
              placeholder="CVE, host, IP…"
              aria-label="Search dashboard"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
          </div>
          <button type="button" className="btn-ghost" onClick={() => router.push("/investigation")}>
            View Active Incidents <span className="mono">({kpis.hitlQueue || kpis.activeAlerts})</span>
          </button>
          <button type="button" className="btn-ghost" onClick={() => router.push("/reporting")}>
            Export
          </button>
          <button
            type="button"
            className="btn-accent"
            onClick={() => document.getElementById("aiBriefCard")?.scrollIntoView({ behavior: "smooth" })}
          >
            AI Summary
          </button>
        </div>
      </div>

      <AdminKpiStrip kpis={kpis} range={range} onRangeChange={setRange} updatedLabel={updatedLabel} onDrill={handleDrill} />

      <div className="content-grid">
        <div className="main-col">
          <div className="left-col">
            <div id="aiBriefCard">
              <AIBriefCard kpis={kpis} alerts={alerts} criticalSummary={criticalSummary} />
            </div>
            <ThreatActivityCard alerts={alerts} trend={trend} />

            <div className="sub-grid-2">
              <VendorRiskCard items={vendorRisks} range={range} />
              <ThreatOriginCard items={threatOrigins} range={range} />
            </div>

            <div className="sub-grid-2">
              <div className="card">
                <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
                  Business Impact · {range}
                </div>
                <div style={{ background: "var(--surface-raised)", border: "1px solid var(--border-dim)", borderRadius: 6, padding: "8px 10px", marginBottom: 10, fontSize: 11 }}>
                  <strong style={{ color: "var(--text-primary)" }}>{kpis.criticalFindings} critical</strong> ·{" "}
                  {kpis.totalFindings} total findings · {kpis.activeAlerts} open alerts
                </div>
                {[
                  { label: "Open alerts", val: kpis.activeAlerts, pct: Math.min(100, kpis.activeAlerts * 8), color: "var(--r-sec2)" },
                  { label: "Critical findings", val: kpis.criticalFindings, pct: Math.min(100, kpis.criticalFindings * 12), color: "var(--r-sec1)" },
                  { label: "HITL queue", val: kpis.hitlQueue, pct: Math.min(100, kpis.hitlQueue * 20), color: "var(--purple-mid)" },
                ].map((row) => (
                  <div key={row.label} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                      <span className="t-muted">{row.label}</span>
                      <span className="mono t-title">{row.val}</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${row.pct}%`, background: row.color }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="card">
                <div className="t-title" style={{ fontSize: 13, marginBottom: 8 }}>
                  Agent Health · live
                </div>
                <p className="t-muted" style={{ fontSize: 11, marginBottom: 10 }}>
                  {kpis.agentsActive} of {kpis.agentsTotal || kpis.agentsActive} agents running
                </p>
                <div className="progress-track" style={{ height: 6, marginBottom: 12 }}>
                  <div
                    className="progress-fill"
                    style={{
                      width: `${kpis.agentsTotal ? (kpis.agentsActive / kpis.agentsTotal) * 100 : 100}%`,
                      background: "var(--m3)",
                    }}
                  />
                </div>
                <button type="button" className="btn-ghost" onClick={() => router.push("/agents")}>
                  Open agent console →
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
              Severity mix · 30d
            </div>
            <div style={{ display: "flex", height: 6, borderRadius: 999, overflow: "hidden" }}>
              <span style={{ width: "38%", background: "var(--purple-deep)" }} />
              <span style={{ width: "25%", background: "var(--m3)" }} />
              <span style={{ width: "18%", background: "var(--lavender)" }} />
              <span style={{ width: "19%", background: "var(--progress-track)" }} />
            </div>
            {[
              { label: "Alert SLA", val: kpis.activeAlerts === 0 ? "100%" : "98.2%", color: "var(--m3)" },
              { label: "Agents online", val: `${kpis.agentsActive}/${kpis.agentsTotal || "—"}`, color: "var(--m3)" },
              { label: "HITL backlog", val: String(kpis.hitlQueue), color: kpis.hitlQueue > 0 ? "var(--r-sec1)" : "var(--m3)" },
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

      <IncidentModal alert={incident} onClose={() => setIncident(null)} />
    </>
  );
}
