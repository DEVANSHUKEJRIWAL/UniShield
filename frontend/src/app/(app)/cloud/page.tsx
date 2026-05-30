"use client";

import { motion } from "framer-motion";
import { AnimatedCard } from "@/components/ui/AnimatedCard";
import { GradientText } from "@/components/ui/primitives";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

const RESOURCES = [
  { name: "s3-logs-prod", type: "S3", issue: "Public read ACL", severity: "high" as const },
  { name: "eks-cluster", type: "EKS", issue: "Outdated node group", severity: "medium" as const },
  { name: "iam-admin-role", type: "IAM", issue: "Overprivileged policy", severity: "critical" as const },
  { name: "rds-backup", type: "RDS", issue: "Encryption at rest disabled", severity: "high" as const },
];

export default function CloudPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-extrabold"><GradientText>Cloud Posture</GradientText></h1>
      <div className="grid gap-4 md:grid-cols-2">
        {RESOURCES.map((r, i) => (
          <AnimatedCard key={r.name} delay={i * 0.08} float>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-bold">{r.name}</p>
                <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">{r.type}</p>
              </div>
              <SeverityBadge severity={r.severity} />
            </div>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">{r.issue}</p>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="mt-4 rounded-lg px-3 py-1.5 text-[10px] font-bold text-white"
              style={{ background: "var(--violet)" }}
            >
              Remediate
            </motion.button>
          </AnimatedCard>
        ))}
      </div>
    </div>
  );
}
