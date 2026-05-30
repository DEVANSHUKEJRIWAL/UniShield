const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchAgentStatus(token?: string | null) {
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}/agent/status`, { headers });
  if (!res.ok) throw new Error("Agent status fetch failed");
  return res.json();
}

export async function fetchDashboard(clientId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/dashboard/${clientId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Dashboard fetch failed");
  return res.json();
}

export async function fetchExecutiveDashboard(clientId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/dashboard/executive/${clientId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Executive dashboard fetch failed");
  return res.json();
}

export async function fetchAlerts(clientId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/alerts/${clientId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Alerts fetch failed");
  const data = await res.json();
  return Array.isArray(data) ? data : data.items ?? [];
}

export async function fetchFindings(clientId: string, token: string, page = 1) {
  const res = await fetch(`${API_BASE}/api/v1/findings/${clientId}?page=${page}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Findings fetch failed");
  return res.json();
}

export async function fetchReportingSummary(clientId: string, token: string, period = "30d") {
  const res = await fetch(`${API_BASE}/api/v1/reporting/${clientId}/summary?period=${period}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Reporting summary fetch failed");
  return res.json();
}

export async function fetchInvestigationCases(clientId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/investigation/cases/${clientId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Investigation cases fetch failed");
  return res.json();
}

export async function fetchInvestigationCase(caseId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/investigation/${caseId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Investigation case fetch failed");
  return res.json();
}

export async function decideHITL(
  actionId: string,
  clientId: string,
  token: string,
  decision: "accept" | "modify" | "reject",
  original?: Record<string, unknown>
) {
  const res = await fetch(`${API_BASE}/api/v1/hitl/${actionId}/decide?client_id=${clientId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ decision, original }),
  });
  if (!res.ok) throw new Error("HITL decision failed");
  return res.json();
}

export async function fetchHITLQueue(clientId: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/hitl/queue/${clientId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("HITL queue fetch failed");
  return res.json();
}

export async function fetchCompliance(clientId: string, framework: string, token: string) {
  const res = await fetch(`${API_BASE}/api/v1/compliance/${clientId}/${framework}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Compliance fetch failed");
  return res.json();
}

export async function fetchClients(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/admin/clients`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Clients fetch failed");
  return res.json();
}

export function agentRunStream(agentName: string, tenantId: string, input: Record<string, unknown>) {
  return fetch(`${API_BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_name: agentName, tenant_id: tenantId, input }),
  });
}

export function agentOrchestrateStream(tenantId: string, event: Record<string, unknown>) {
  return fetch(`${API_BASE}/agent/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_id: tenantId, event }),
  });
}

export function agentWsUrl(clientId: string) {
  const base = API_BASE.replace("http", "ws");
  return `${base}/api/v1/agents/stream/${clientId}`;
}

export function wsUrl(clientId: string) {
  const base = API_BASE.replace("http", "ws");
  return `${base}/api/v1/ws/${clientId}`;
}
