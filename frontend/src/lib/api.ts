const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchAgentStatus(): Promise<{ agents: Array<{ name: string; status: string }> }> {
  const res = await fetch(`${API_BASE}/agent/status`);
  if (!res.ok) throw new Error("Agent status fetch failed");
  return res.json();
}

export function agentRunStream(agentName: string, tenantId: string, input: Record<string, unknown>) {
  return fetch(`${API_BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_name: agentName, tenant_id: tenantId, input }),
  });
}
