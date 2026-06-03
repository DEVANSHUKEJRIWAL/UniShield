import { authFetch } from "@/lib/api";

export type WorkflowStatus = "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED";

export type WorkflowSummary = {
  workflow_id: string;
  client_id: string;
  workflow_name: string;
  flow_type: string;
  triggered_by: string;
  started_at: string;
  completed_at?: string | null;
  status: WorkflowStatus;
  error?: string | null;
  agent_states: Record<string, string>;
  current_step_index: number;
  paused: boolean;
  pause_reason?: string | null;
};

export type WorkflowDefinition = {
  label: string;
  description: string;
  estimated_minutes: number;
  steps: string[][];
};

export type WorkflowOutput = {
  workflow_id: string;
  client_id: string;
  checksum: string;
  completed_at: string;
  snapshot: Record<string, Record<string, unknown>>;
};

export type WorkflowMetrics = {
  available: boolean;
  source?: string;
  running_workflows?: number;
  completed_workflows?: number;
  failed_workflows?: number;
  kpis?: {
    risk_score: number;
    risk_label: string;
    total_findings: number;
    critical_findings: number;
    active_alerts: number;
  };
  priority_queue?: Array<{
    id: string;
    severity: string;
    title: string;
    source: string;
    time: string;
    workflow_id?: string;
    file_path?: string;
  }>;
  agents_active?: number;
  agents_total?: number;
};

async function workflowsFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, token, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Workflow API error ${res.status}`);
  }
  return res.json();
}

export async function fetchWorkflowHealth(token: string) {
  return workflowsFetch<{ reachable: boolean; orchestrator?: { status: string }; error?: string }>(
    "/api/v1/workflows/health",
    token
  );
}

export async function fetchWorkflowDefinitions(token: string) {
  return workflowsFetch<Record<string, WorkflowDefinition>>("/api/v1/workflows/definitions", token);
}

export async function fetchWorkflows(
  clientId: string,
  token: string,
  params?: { status?: string; limit?: number }
) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return workflowsFetch<WorkflowSummary[]>(
    `/api/v1/workflows/${clientId}${query ? `?${query}` : ""}`,
    token
  );
}

export async function fetchWorkflow(clientId: string, workflowId: string, token: string) {
  return workflowsFetch<WorkflowSummary>(`/api/v1/workflows/${clientId}/${workflowId}`, token);
}

export async function fetchWorkflowOutput(clientId: string, workflowId: string, token: string) {
  return workflowsFetch<WorkflowOutput>(
    `/api/v1/workflows/${clientId}/${workflowId}/output`,
    token
  );
}

export async function triggerWorkflow(
  clientId: string,
  token: string,
  body: {
    workflow_id: string;
    repo_url?: string;
    repo_ref?: string;
    source?: string;
  }
) {
  return workflowsFetch<{ workflow_id: string; status: string; estimated_minutes: number }>(
    `/api/v1/workflows/${clientId}/trigger`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ ...body, client_id: clientId, source: body.source ?? "manual_frontend" }),
    }
  );
}

export async function fetchWorkflowMetrics(clientId: string, token: string) {
  return workflowsFetch<WorkflowMetrics>(`/api/v1/workflows/metrics/${clientId}`, token);
}

export async function approveWorkflow(
  clientId: string,
  workflowId: string,
  token: string,
  approvedBy: string
) {
  return workflowsFetch<{ workflow_id: string; status: string }>(
    `/api/v1/workflows/${clientId}/${workflowId}/approve`,
    token,
    { method: "POST", body: JSON.stringify({ approved_by: approvedBy }) }
  );
}
