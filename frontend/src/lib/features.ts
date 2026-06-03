/** Feature flags for gradual orchestrator UI rollout. */

export const features = {
  /** Show Security Workflows nav + pages */
  orchestratorUi: process.env.NEXT_PUBLIC_ORCHESTRATOR_UI === "true",
  /** Merge orchestrator KPIs into Admin Center dashboard */
  orchestratorDashboardMetrics:
    process.env.NEXT_PUBLIC_ORCHESTRATOR_DASHBOARD_METRICS === "true",
};
