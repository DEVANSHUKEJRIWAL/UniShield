"""Orchestrator Agent — LangGraph multi-agent routing (Week 2)."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents._openclaw.base import OpenClawAgent
from agents.orchestrator.routing import resolve_priority, select_agents_for_event
from packages.core.dispatch import aggregate_results, dispatch_agents, publish_aggregated_finding
from packages.shared_types.constants import AgentName


class OrchestratorState(TypedDict):
    """LangGraph state for orchestrator workflows."""

    event: dict[str, Any]
    tenant_id: str
    kg_context: dict[str, Any]
    priority: str
    target_agents: list[str]
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
        event = state["event"]
        state["priority"] = resolve_priority(event)
        state["target_agents"] = select_agents_for_event(event)
        return state

    async def _dispatch_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Dispatch parallel/sequential agent tasks with retry."""
        results = await dispatch_agents(
            event=state["event"],
            tenant_id=state["tenant_id"],
            agent_names=state["target_agents"],
            priority=state["priority"],
            mode="inline",
            parent_event_id=state["event"].get("event_id"),
        )
        state["agent_results"] = [r.model_dump(mode="json") for r in results]
        return state

    async def _aggregate_results(self, state: OrchestratorState) -> OrchestratorState:
        """Aggregate findings from multiple agents and publish."""
        from packages.core.agent_messages import AgentResultMessage

        parsed = [AgentResultMessage.model_validate(r) for r in state.get("agent_results", [])]
        aggregated = aggregate_results(state["tenant_id"], state["event"], parsed)
        state["aggregated_finding"] = aggregated.model_dump(mode="json")
        await publish_aggregated_finding(aggregated)
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
        """Execute orchestrator tool calls — publishes to Redis task streams."""
        from packages.core.agent_messages import AgentTaskMessage

        if tool_name == "dispatch_agent":
            agent_name = tool_input.get("agent_name", "")
            if agent_name not in {n.value for n in AgentName} or agent_name == AgentName.ORCHESTRATOR:
                return {"status": "error", "message": f"Invalid agent: {agent_name}"}
            msg = AgentTaskMessage(
                tenant_id=self.tenant_id,
                priority=tool_input.get("priority", "P2"),
                input=tool_input.get("task", {}),
                triggered_by=self.agent_name,
            )
            from packages.core.dispatch import publish_agent_task

            msg_id = await publish_agent_task(msg, agent_name)
            return {"status": "queued", "agent": agent_name, "task_id": msg.task_id, "stream_id": msg_id}
        if tool_name == "aggregate_findings":
            return {"status": "aggregated", "count": len(tool_input.get("finding_ids", []))}
        return {"error": f"Unknown tool: {tool_name}"}

    async def on_event(self, event: dict[str, Any]) -> None:
        """Route incoming event through LangGraph workflow."""
        tenant_id = event.get("tenant_id", self.tenant_id)
        initial_state: OrchestratorState = {
            "event": event.get("input", event),
            "tenant_id": tenant_id,
            "kg_context": event.get("context", {}),
            "priority": "P2",
            "target_agents": [],
            "agent_results": [],
            "aggregated_finding": None,
        }
        compiled = self.graph.compile()
        await compiled.ainvoke(initial_state)

    async def orchestrate(self, event: dict[str, Any]) -> dict[str, Any]:
        """Run full orchestration pipeline and return aggregated result."""
        initial_state: OrchestratorState = {
            "event": event,
            "tenant_id": self.tenant_id,
            "kg_context": {},
            "priority": "P2",
            "target_agents": [],
            "agent_results": [],
            "aggregated_finding": None,
        }
        compiled = self.graph.compile()
        final = await compiled.ainvoke(initial_state)
        return {
            "priority": final.get("priority"),
            "agents": final.get("target_agents"),
            "results": final.get("agent_results"),
            "aggregated": final.get("aggregated_finding"),
        }
