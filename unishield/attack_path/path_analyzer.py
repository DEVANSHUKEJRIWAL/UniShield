"""Analyze attack paths, chokepoints, and blast radius."""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Optional

import networkx as nx

from unishield.schemas.attack_path_schemas import (
    AttackEdge,
    AttackNode,
    AttackPath,
    BlastRadius,
    Chokepoint,
    EdgeType,
    NodeType,
)


class AttackPathAnalyzer:
    """Queries NetworkX graph for attack paths and remediation priorities."""

    SINK_SEVERITY = {
        "injection": 1.0,
        "command_injection": 1.0,
        "deserialization": 0.9,
        "code_execution": 1.0,
        "path_traversal": 0.7,
        "ssrf": 0.6,
        "sql_injection": 1.0,
    }

    def __init__(
        self,
        nx_graph: nx.DiGraph,
        scan_id: str,
        model_router: Any | None = None,
        neo4j_driver: Any | None = None,
    ) -> None:
        self.graph = nx_graph
        self.scan_id = scan_id
        self.router = model_router
        self.driver = neo4j_driver

    async def find_all_paths(self, max_depth: int = 15, limit: int = 100) -> list[AttackPath]:
        paths: list[AttackPath] = []
        entry_nodes = [
            data for _, data in self.graph.nodes(data=True) if data.get("node_type") == NodeType.ENTRY_POINT.value
        ]
        sink_nodes = [
            (node_id, data)
            for node_id, data in self.graph.nodes(data=True)
            if data.get("node_type") == NodeType.SINK.value
        ]

        for entry_data in entry_nodes:
            entry_id = entry_data["node_id"]
            for sink_id, sink_data in sink_nodes:
                try:
                    for node_ids in nx.all_simple_paths(self.graph, entry_id, sink_id, cutoff=max_depth):
                        if len(paths) >= limit:
                            break
                        path = await self._build_path(node_ids, entry_data, sink_data)
                        path.risk_score = self._score_path(path)
                        paths.append(path)
                except nx.NetworkXNoPath:
                    continue
            if len(paths) >= limit:
                break

        return sorted(paths, key=lambda p: p.risk_score, reverse=True)[:limit]

    async def find_chokepoints(self, paths: list[AttackPath]) -> list[Chokepoint]:
        node_counts: Counter[str] = Counter()
        node_map: dict[str, AttackNode] = {}
        for path in paths:
            for node in path.nodes[1:-1]:
                node_counts[node.node_id] += 1
                node_map[node.node_id] = node

        total_paths = len(paths) if paths else 1
        chokepoints: list[Chokepoint] = []
        for node_id, count in node_counts.most_common(10):
            node = node_map[node_id]
            chokepoints.append(
                Chokepoint(
                    node=node,
                    paths_blocked=count,
                    blocking_score=count / total_paths,
                    fix_effort=self._estimate_fix_effort(node),
                    recommended_fix=await self._generate_chokepoint_fix(node),
                )
            )
        return chokepoints

    async def compute_blast_radii(
        self,
        entry_points: list[AttackNode],
        paths: list[AttackPath],
    ) -> list[BlastRadius]:
        blast_radii: list[BlastRadius] = []
        for entry in entry_points:
            entry_paths = [p for p in paths if p.entry_point.node_id == entry.node_id]
            if not entry_paths:
                continue
            reachable_sinks = list({p.sink.node_id: p.sink for p in entry_paths}.values())
            reachable_cj = list(
                {p.crown_jewel_name for p in entry_paths if p.reaches_crown_jewel and p.crown_jewel_name}
            )
            max_depth = max((p.path_length for p in entry_paths), default=0)
            blast_score = min(
                100.0,
                float(len(reachable_sinks) * 10 + len(reachable_cj) * 25 + max_depth * 2),
            )
            blast_radii.append(
                BlastRadius(
                    entry_point=entry,
                    reachable_sinks=reachable_sinks,
                    reachable_crown_jewels=reachable_cj,
                    total_paths=len(entry_paths),
                    max_path_depth=max_depth,
                    blast_score=blast_score,
                    worst_case_impact=self._describe_worst_case(entry, reachable_sinks, reachable_cj),
                )
            )
        return sorted(blast_radii, key=lambda b: b.blast_score, reverse=True)

    async def _build_path(
        self,
        node_ids: list[str],
        entry_data: dict[str, Any],
        sink_data: dict[str, Any],
    ) -> AttackPath:
        nodes = [self._node_from_graph(node_id) for node_id in node_ids]
        edges: list[AttackEdge] = []
        for src, tgt in zip(node_ids, node_ids[1:]):
            edge_data = self.graph.get_edge_data(src, tgt) or {}
            edges.append(
                AttackEdge(
                    edge_id=edge_data.get("edge_id", str(uuid.uuid4())),
                    source_node_id=src,
                    target_node_id=tgt,
                    edge_type=EdgeType(edge_data.get("edge_type", EdgeType.REACHES_SINK.value)),
                    tainted=bool(edge_data.get("tainted", True)),
                    sanitized=bool(edge_data.get("sanitized", False)),
                    call_site_file=edge_data.get("call_site_file", ""),
                    call_site_line=int(edge_data.get("call_site_line") or 0),
                    scan_id=self.scan_id,
                )
            )
        entry = nodes[0]
        sink = nodes[-1]
        has_sanitizer = any(n.is_sanitizer for n in nodes)
        reaches_cj = any(n.is_crown_jewel for n in nodes)
        narrative = await self._generate_attack_narrative(entry, sink, has_sanitizer, reaches_cj)
        return AttackPath(
            path_id=str(uuid.uuid4()),
            scan_id=self.scan_id,
            nodes=nodes,
            edges=edges,
            entry_point=entry,
            sink=sink,
            path_length=len(nodes) - 1,
            has_sanitizer=has_sanitizer,
            risk_score=0.0,
            exploitability=0.5,
            stride_threats=[],
            reaches_crown_jewel=reaches_cj,
            crown_jewel_name=next((n.name for n in nodes if n.is_crown_jewel), None),
            description=f"{entry.name} → {sink.name}",
            attack_narrative=narrative,
            remediation="Add input validation or parameterized queries at the sink.",
        )

    def _node_from_graph(self, node_id: str) -> AttackNode:
        data = self.graph.nodes[node_id]
        return AttackNode(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]),
            name=data.get("name", node_id),
            file_path=data.get("file_path", ""),
            line_start=int(data.get("line_start") or 0),
            line_end=int(data.get("line_end") or 0),
            language=data.get("language", "unknown"),
            is_crown_jewel=bool(data.get("is_crown_jewel")),
            is_sanitizer=bool(data.get("is_sanitizer")),
            metadata=data.get("metadata", {}),
            scan_id=self.scan_id,
        )

    def _score_path(self, path: AttackPath) -> float:
        crown = 1.0 if path.reaches_crown_jewel else 0.0
        no_san = 0.0 if path.has_sanitizer else 1.0
        short = max(0.0, 1.0 - (path.path_length / 15))
        severe = self.SINK_SEVERITY.get(path.sink.metadata.get("sink_type", ""), 0.5)
        return crown * 40 + no_san * 30 + short * 20 + severe * 10

    def _estimate_fix_effort(self, node: AttackNode) -> str:
        if node.node_type == NodeType.SANITIZER:
            return "LOW"
        if node.node_type == NodeType.ENTRY_POINT:
            return "HIGH"
        return "MEDIUM"

    async def _generate_chokepoint_fix(self, node: AttackNode) -> str:
        if self.router is None:
            return f"Harden {node.name} in {node.file_path} with validation before downstream sinks."
        from unishield.infrastructure.model_router import TaskType

        prompt = (
            f"Recommend one fix for chokepoint function {node.name} "
            f"in {node.file_path}:{node.line_start}."
        )
        try:
            return await self.router.complete(task_type=TaskType.CODE_ANALYSIS, prompt=prompt, max_tokens=150)
        except Exception:
            return f"Harden {node.name} in {node.file_path} with validation before downstream sinks."

    async def _generate_attack_narrative(
        self,
        entry: AttackNode,
        sink: AttackNode,
        has_sanitizer: bool,
        reaches_cj: bool,
    ) -> str:
        if self.router is None:
            return (
                f"Attacker sends crafted input to {entry.name}, which flows to "
                f"{sink.name} ({sink.metadata.get('sink_type', 'sink')})."
            )
        from unishield.infrastructure.model_router import TaskType

        prompt = (
            f"Write a 3-sentence attack narrative from entry {entry.name} "
            f"to sink {sink.name} ({sink.metadata.get('sink_type')}). "
            f"Sanitizer present: {has_sanitizer}. Crown jewel: {reaches_cj}."
        )
        try:
            return await self.router.complete(task_type=TaskType.THREAT_INTEL, prompt=prompt, max_tokens=300)
        except Exception:
            return (
                f"Attacker sends crafted input to {entry.name}, which flows to "
                f"{sink.name} ({sink.metadata.get('sink_type', 'sink')})."
            )

    def _describe_worst_case(
        self,
        entry: AttackNode,
        sinks: list[AttackNode],
        crown_jewels: list[str],
    ) -> str:
        if crown_jewels:
            return f"Attacker exploiting {entry.name} can reach crown jewels: {', '.join(crown_jewels)}"
        sink_types = list({s.metadata.get("sink_type", "unknown") for s in sinks})
        return f"Attacker exploiting {entry.name} can reach {len(sinks)} sink(s): {', '.join(sink_types[:3])}"
