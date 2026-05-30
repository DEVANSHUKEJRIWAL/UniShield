"""Orchestrator Agent — LangGraph multi-agent routing."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents._openclaw.base import OpenClawAgent
from packages.shared_types.constants import AgentName


class OrchestratorState(TypedDict):
    """LangGraph state for orchestrator workflows."""

    event: dict[str, Any]
    tenant_id: str
    kg_context: dict[str, Any]
    agent_results: list[dict[str, Any]]
    aggregated_finding: dict[str, Any] | None


class OrchestratorAgent(OpenClawAgent):
    """Central task router with LangGraph multi-agent dispatch."""

    PRIORITY_LEVELS = ("P0", "P1", "P2", "P3")

    def __init__(self, agent_id: str, tenant_id: str, **kwargs: Any) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_name=AgentName.ORCHESTRATOR,
            tenant_id=tenant_id,
            **kwargs,
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for multi-agent routing."""
        graph = StateGraph(OrchestratorState)
        graph.add_node("route", self._route_event)
        graph.add_node("dispatch", self._dispatch_agents)
        graph.add_node("aggregate", self._aggregate_results)
        graph.set_entry_point("route")
        graph.add_edge("route", "dispatch")
        graph.add_edge("dispatch", "aggregate")
        graph.add_edge("aggregate", END)
        return graph

    async def _route_event(self, state: OrchestratorState) -> OrchestratorState:
        """Determine priority and target agents for the event."""
        return state

    async def _dispatch_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Dispatch parallel agent tasks based on event type."""
        state["agent_results"] = []
        return state

    async def _aggregate_results(self, state: OrchestratorState) -> OrchestratorState:
        """Aggregate findings from multiple agents."""
        state["aggregated_finding"] = {
            "contributing_agents": [],
            "findings": state.get("agent_results", []),
        }
        return state

    def get_system_prompt(self, kg_context: dict[str, Any]) -> str:
        """Return orchestrator system prompt."""
        return (
            "You are the UniShield Orchestrator Agent. Route security events to specialist "
            f"agents, manage priority queues (P0-P3), and aggregate findings. "
            f"Tenant: {self.tenant_id}. KG context: {kg_context}"
        )

    async def get_tools(self) -> list[dict[str, Any]]:
        """Return orchestrator tool schemas."""
        return [
            {
                "name": "dispatch_agent",
                "description": "Dispatch a task to a specialist agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {"type": "string"},
                        "task": {"type": "object"},
                        "priority": {"type": "string", "enum": list(self.PRIORITY_LEVELS)},
                    },
                    "required": ["agent_name", "task"],
                },
            },
            {
                "name": "aggregate_findings",
                "description": "Aggregate findings from multiple agents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "finding_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["finding_ids"],
                },
            },
        ]

    async def handle_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Execute orchestrator tool calls."""
        if tool_name == "dispatch_agent":
            return {"status": "queued", "agent": tool_input.get("agent_name")}
        if tool_name == "aggregate_findings":
            return {"status": "aggregated", "count": len(tool_input.get("finding_ids", []))}
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Route incoming event through LangGraph workflow."""
        initial_state: OrchestratorState = {
            "event": event,
            "tenant_id": self.tenant_id,
            "kg_context": {},
            "agent_results": [],
            "aggregated_finding": None,
        }
        compiled = self.graph.compile()
        await compiled.ainvoke(initial_state)
