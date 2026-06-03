import { authFetch } from "@/lib/api";

export type VCSProvider = "github" | "gitlab" | "bitbucket";
export type RepoStatus = "connected" | "auth_failed" | "not_found" | "rate_limited" | "pending";

export type RepoConnection = {
  connection_id: string;
  client_id: string;
  provider: VCSProvider;
  auth_method: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  default_branch: string;
  description?: string | null;
  is_crown_jewel: boolean;
  crown_jewel_paths: string[];
  exclude_patterns: string[];
  include_languages: string[];
  status: RepoStatus;
  last_verified_at?: string | null;
  last_scanned_at?: string | null;
  last_scan_id?: string | null;
  error_message?: string | null;
  registered_at: string;
  registered_by: string;
  updated_at?: string | null;
};

export type ConnectRepoPayload = {
  connection: {
    client_id: string;
    provider: VCSProvider;
    auth_method?: string;
    repo_url: string;
    repo_owner: string;
    repo_name: string;
    default_branch?: string;
    description?: string;
    is_crown_jewel?: boolean;
    crown_jewel_paths?: string[];
    registered_by: string;
  };
  token: string;
};

async function reposFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, token, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Repos API error ${res.status}`);
  }
  return res.json();
}

export async function fetchRepos(clientId: string, token: string) {
  return reposFetch<RepoConnection[]>(`/api/v1/repos/${clientId}`, token);
}

export async function connectRepo(token: string, body: ConnectRepoPayload) {
  return reposFetch<RepoConnection>("/api/v1/repos/connect", token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function verifyRepo(clientId: string, connectionId: string, token: string) {
  return reposFetch<RepoConnection>(
    `/api/v1/repos/${clientId}/connection/${connectionId}/verify`,
    token,
    { method: "POST" }
  );
}

export async function deleteRepo(clientId: string, connectionId: string, token: string) {
  return reposFetch<{ deleted: boolean }>(
    `/api/v1/repos/${clientId}/connection/${connectionId}`,
    token,
    { method: "DELETE" }
  );
}

export async function scanRepo(
  clientId: string,
  connectionId: string,
  token: string,
  body: { workflow_id: string; ref_override?: string; scan_mode?: string }
) {
  return reposFetch<{ workflow_id: string; status: string; connection_id: string }>(
    `/api/v1/repos/${clientId}/connection/${connectionId}/scan`,
    token,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export async function fetchRepoBranches(clientId: string, connectionId: string, token: string) {
  return reposFetch<{ branches: string[] }>(
    `/api/v1/repos/${clientId}/connection/${connectionId}/branches`,
    token
  );
}
