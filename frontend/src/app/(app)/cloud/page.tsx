"use client";

import { Sidebar } from "@/components/Sidebar";

export default function CloudPage() {
  const resources = [
    { name: "s3-logs-prod", type: "S3", issue: "Public read ACL", severity: "high" },
    { name: "eks-cluster", type: "EKS", issue: "Outdated node group", severity: "medium" },
    { name: "iam-admin-role", type: "IAM", issue: "Overprivileged policy", severity: "critical" },
  ];
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">Cloud Posture</h1>
        <div className="mt-6 space-y-3">
          {resources.map((r) => (
            <div key={r.name} className="obsidian-card flex justify-between">
              <div><p className="font-medium">{r.name}</p><p className="mono text-xs text-[var(--text-muted)]">{r.type}</p></div>
              <div className="text-right"><p className="text-sm">{r.issue}</p><p className="mono text-xs text-[var(--danger)]">{r.severity}</p></div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
