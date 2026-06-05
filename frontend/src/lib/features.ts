/** Feature flags — orchestrator-focused defaults (opt out with env=false). */

const envFalse = (key: string) => process.env[key] === "false";

export const features = {
  /** Show Security Workflows nav + pages */
  orchestratorUi: !envFalse("NEXT_PUBLIC_ORCHESTRATOR_UI"),
  /** Dashboard + sidebar use workflow metrics (not legacy agent WebSocket) */
  orchestratorDashboardMetrics: !envFalse("NEXT_PUBLIC_ORCHESTRATOR_DASHBOARD_METRICS"),
};
