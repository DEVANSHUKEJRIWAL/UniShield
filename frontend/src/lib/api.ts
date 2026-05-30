const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

async function authFetch(path: string, token: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (res.status === 401) {
    unauthorizedHandler?.();
    throw new Error("Unauthorized — please log in again");
  }
  return res;
}

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
  const res = await authFetch(`/api/v1/dashboard/${clientId}`, token);
  if (!res.ok) throw new Error("Dashboard fetch failed");
  return res.json();
}

export async function fetchExecutiveDashboard(clientId: string, token: string) {
  const res = await authFetch(`/api/v1/dashboard/executive/${clientId}`, token);
  if (!res.ok) throw new Error("Executive dashboard fetch failed");
  return res.json();
}

export async function fetchAlerts(clientId: string, token: string) {
  const res = await authFetch(`/api/v1/alerts/${clientId}`, token);
  if (!res.ok) throw new Error("Alerts fetch failed");
  return res.json();
}

export async function fetchAgentHealth(clientId: string, token: string) {
  const res = await authFetch(`/api/v1/agents/status/${clientId}`, token);
  if (!res.ok) throw new Error("Agent health fetch failed");
  return res.json();
}

export async function fetchHITLQueue(clientId: string, token: string) {
  const res = await authFetch(`/api/v1/hitl/queue/${clientId}`, token);
  if (!res.ok) throw new Error("HITL queue fetch failed");
  return res.json();
}

export async function fetchCompliance(clientId: string, framework: string, token: string) {
  const res = await authFetch(`/api/v1/compliance/${clientId}/${framework}`, token);
  if (!res.ok) throw new Error("Compliance fetch failed");
  return res.json();
}

export async function fetchClients(token: string) {
  const res = await authFetch("/api/v1/admin/clients", token);
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

export function wsUrl(clientId: string) {
  const base = API_BASE.replace("http", "ws");
  return `${base}/api/v1/ws/${clientId}`;
}
