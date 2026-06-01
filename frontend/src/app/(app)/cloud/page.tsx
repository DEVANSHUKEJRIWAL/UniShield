"use client";

import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { AdminPageHeader } from "@/components/admin-center/AdminPageHeader";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

const RESOURCES = [
  { name: "s3-logs-prod", type: "S3", issue: "Public read ACL", severity: "high" as const },
  { name: "eks-cluster", type: "EKS", issue: "Outdated node group", severity: "medium" as const },
  { name: "iam-admin-role", type: "IAM", issue: "Overprivileged policy", severity: "critical" as const },
  { name: "rds-backup", type: "RDS", issue: "Encryption at rest disabled", severity: "high" as const },
];

export default function CloudPage() {
  return (
    <>
      <AdminPageHeader title="Cloud Security" subtitle="CSPM findings and remediation queue" />

      <div className="ac-grid-2">
        {RESOURCES.map((r, i) => (
          <AnimatedCard key={r.name} delay={i * 0.08}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-bold">{r.name}</p>
                <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">{r.type}</p>
              </div>
              <SeverityBadge severity={r.severity} />
            </div>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">{r.issue}</p>
            <button type="button" className="btn-accent mt-4" style={{ padding: "6px 14px", fontSize: 11 }}>
              Remediate
            </button>
          </AnimatedCard>
        ))}
      </div>
    </>
  );
}
