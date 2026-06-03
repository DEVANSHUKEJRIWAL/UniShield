"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  fetchWorkflow,
  fetchWorkflowOutput,
  fetchWorkflows,
  type WorkflowOutput,
  type WorkflowSummary,
} from "@/lib/workflows-api";

export function useWorkflowList(statusFilter?: string) {
  const { token, tenantId, ready } = useAuth();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!token || !tenantId) return;
    setLoading(true);
    setError(null);
    fetchWorkflows(tenantId, token, { status: statusFilter, limit: 50 })
      .then(setWorkflows)
      .catch((e: Error) => {
        setError(e.message);
        setWorkflows([]);
      })
      .finally(() => setLoading(false));
  }, [token, tenantId, statusFilter]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    refresh();
  }, [ready, token, tenantId, refresh]);

  return { workflows, loading, error, refresh };
}

export function useWorkflowDetail(workflowId: string) {
  const { token, tenantId, ready } = useAuth();
  const [workflow, setWorkflow] = useState<WorkflowSummary | null>(null);
  const [output, setOutput] = useState<WorkflowOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!token || !tenantId || !workflowId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchWorkflow(tenantId, workflowId, token),
      fetchWorkflowOutput(tenantId, workflowId, token).catch(() => null),
    ])
      .then(([wf, out]) => {
        setWorkflow(wf);
        setOutput(out);
      })
      .catch((e: Error) => {
        setError(e.message);
        setWorkflow(null);
        setOutput(null);
      })
      .finally(() => setLoading(false));
  }, [token, tenantId, workflowId]);

  useEffect(() => {
    if (!ready || !token || !tenantId) return;
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [ready, token, tenantId, refresh]);

  return { workflow, output, loading, error, refresh };
}
