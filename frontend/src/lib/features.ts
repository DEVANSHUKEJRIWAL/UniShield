/** Feature flags for orchestrator UI — enabled by default unless explicitly disabled. */

const disabled = (value: string | undefined) => value === "false";

export const features = {
  orchestratorUi: !disabled(process.env.NEXT_PUBLIC_ORCHESTRATOR_UI),
  orchestratorDashboardMetrics: !disabled(process.env.NEXT_PUBLIC_ORCHESTRATOR_DASHBOARD_METRICS),
};
