/** Parse live SCR snapshot fields (handles stringified JSON from Redis). */

export type ScrFinding = {
  finding_id?: string;
  file_path?: string;
  line_start?: number;
  line_end?: number;
  severity?: string;
  category?: string;
  cwe_id?: string;
  confidence?: number;
  false_positive_score?: number;
  code_snippet?: string;
  rule_id?: string;
  tool?: string;
  language?: string;
  data_flow?: string[];
  reachable_from?: string[];
  call_chain?: string[];
  ai_explanation?: string | null;
  ai_attack_scenario?: string | null;
  ai_business_impact?: string | null;
  ai_fix?: string | null;
  ai_fix_code?: string | null;
  exploited_in_wild?: boolean;
  incident_relevance?: boolean;
  crown_jewel_boost?: boolean;
};

export type ScrSecret = {
  secret_type?: string;
  file_path?: string;
  line_number?: number;
  masked_value?: string;
  entropy_score?: number;
  verified_live?: boolean;
  git_history_exposed?: boolean;
};

export type ScrDependency = {
  package_name?: string;
  version?: string;
  ecosystem?: string;
  cve_id?: string;
  cvss_score?: number;
  severity?: string;
  fixed_version?: string | null;
};

export type ComplianceGap = {
  framework?: string;
  control?: string;
  category?: string;
  severity?: string;
  status?: string;
  file_path?: string;
  details?: string;
};

export type ScrSnapshot = Record<string, unknown>;

export function coerceList<T>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? (parsed as T[]) : [];
    } catch {
      return [];
    }
  }
  return [];
}

export function coerceDict(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : {};
    } catch {
      return {};
    }
  }
  return {};
}

export function parseScrSnapshot(scr: ScrSnapshot | undefined) {
  if (!scr) {
    return {
      findings: [] as ScrFinding[],
      secrets: [] as ScrSecret[],
      dependencies: [] as ScrDependency[],
      complianceGaps: [] as ComplianceGap[],
      remediationPlan: [] as string[],
      sbom: {} as Record<string, unknown>,
      sbomSummary: {} as Record<string, unknown>,
      attackPaths: {} as Record<string, unknown>,
      analysisStats: {} as Record<string, unknown>,
    };
  }
  return {
    findings: coerceList<ScrFinding>(scr.code_findings).length
      ? coerceList<ScrFinding>(scr.code_findings)
      : coerceList<ScrFinding>(scr.top_findings),
    secrets: coerceList<ScrSecret>(scr.secret_findings),
    dependencies: coerceList<ScrDependency>(scr.dependency_findings),
    complianceGaps: coerceList<ComplianceGap>(scr.compliance_gaps),
    remediationPlan: coerceList<string>(scr.remediation_plan),
    sbom: coerceDict(scr.sbom),
    sbomSummary: coerceDict(scr.sbom_summary),
    attackPaths: coerceDict(scr.attack_paths_summary),
    analysisStats: coerceDict(scr.analysis_stats),
  };
}

export function parseCmaSnapshot(cma: ScrSnapshot | undefined) {
  if (!cma) return { complianceGaps: [] as ComplianceGap[], frameworks: [] as string[] };
  const frameworks = coerceList<string>(cma.frameworks_assessed);
  return {
    complianceGaps: coerceList<ComplianceGap>(cma.compliance_gaps),
    frameworks: frameworks.length ? frameworks : ["PCI-DSS", "SOC2", "ISO27001"],
  };
}

export function severityColor(severity: string): string {
  const s = severity.toUpperCase();
  if (s === "CRITICAL") return "var(--r-sec1)";
  if (s === "HIGH") return "#ea580c";
  if (s === "MEDIUM") return "var(--amber)";
  if (s === "LOW") return "#2563eb";
  return "var(--m3)";
}

export function formatWhen(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const time = d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (sameDay) return `Today at ${time}`;
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function findingDescription(f: ScrFinding): string {
  if (f.ai_explanation) return f.ai_explanation;
  if (f.code_snippet && !f.code_snippet.startsWith("Suspicious path segment")) {
    return f.code_snippet.slice(0, 120);
  }
  return `${f.category ?? "issue"} detected in ${f.file_path ?? "unknown file"}`;
}

export function blastScore(f: ScrFinding): number {
  const sev = { CRITICAL: 12, HIGH: 8, MEDIUM: 5, LOW: 2, INFO: 1 }[String(f.severity).toUpperCase()] ?? 3;
  const reach = (f.reachable_from?.length ?? 0) > 0 ? 2 : 0;
  const fp = (f.false_positive_score ?? 0) > 0.7 ? -4 : 0;
  return sev + reach + fp;
}

export function remediationSteps(f: ScrFinding, plan: string[]): string[] {
  const steps: string[] = [];
  if (f.ai_fix) steps.push(f.ai_fix);
  const match = plan.find((p) => f.file_path && p.includes(f.file_path));
  if (match) steps.push(match);
  if (!steps.length) {
    steps.push(`Review ${f.file_path}:${f.line_start} and apply secure coding fix for ${f.category}.`);
  }
  return steps;
}

export function fixComplexity(f: ScrFinding): "quick-win" | "moderate" | "major refactor" {
  const cat = (f.category ?? "").toLowerCase();
  if (cat.includes("secret") || cat.includes("hardcoded")) return "quick-win";
  if (cat.includes("taint") || cat.includes("injection") || f.severity === "CRITICAL") return "major refactor";
  return "moderate";
}
