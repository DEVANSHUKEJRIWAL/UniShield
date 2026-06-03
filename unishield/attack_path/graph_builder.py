"""Build attack path graph from SCR findings."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Optional

import networkx as nx

from unishield.schemas.attack_path_schemas import AttackEdge, AttackNode, EdgeType, NodeType

logger = logging.getLogger(__name__)

SINK_CATEGORIES = {
    "injection",
    "command_injection",
    "path_traversal",
    "deserialization",
    "code_execution",
    "xxe",
    "ssrf",
    "open_redirect",
    "sql_injection",
}


class AttackPathGraphBuilder:
    """Builds directed attack graph from SCR code findings."""

    def __init__(
        self,
        scan_id: str,
        neo4j_uri: Optional[str] = None,
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
    ) -> None:
        self.scan_id = scan_id
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.nx_graph = nx.DiGraph()
        self._driver = None

    async def build_from_scan_results(
        self,
        code_findings: list[dict[str, Any]],
        file_asts: dict[str, Any] | None = None,
        language_map: dict[str, str] | None = None,
        crown_jewels: list[str] | None = None,
        ioc_list: list[str] | None = None,
    ) -> tuple[list[AttackNode], list[AttackEdge]]:
        crown_jewels = crown_jewels or []
        language_map = language_map or {}
        nodes: list[AttackNode] = []
        edges: list[AttackEdge] = []
        entry_by_file: dict[str, AttackNode] = {}

        for finding in code_findings:
            file_path = str(finding.get("file_path") or "unknown")
            if file_path not in entry_by_file:
                entry = AttackNode(
                    node_id=self._node_id({"file_path": file_path, "name": "entry", "line_start": 0}),
                    node_type=NodeType.ENTRY_POINT,
                    name=f"entry:{file_path}",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    language=language_map.get(file_path, str(finding.get("language", "unknown"))),
                    metadata={"route": file_path},
                    scan_id=self.scan_id,
                )
                entry_by_file[file_path] = entry
                nodes.append(entry)

            category = str(finding.get("category", "unknown")).lower()
            if category not in SINK_CATEGORIES and "inject" not in category:
                continue

            sink = AttackNode(
                node_id=self._node_id(finding),
                node_type=NodeType.SINK,
                name=str(finding.get("function_name") or finding.get("category") or "sink"),
                file_path=file_path,
                line_start=int(finding.get("line_start") or 0),
                line_end=int(finding.get("line_end") or 0),
                language=str(finding.get("language") or language_map.get(file_path, "unknown")),
                is_crown_jewel=any(j in file_path for j in crown_jewels),
                metadata={
                    "sink_type": category,
                    "cwe_id": finding.get("cwe_id"),
                    "severity": finding.get("severity"),
                    "code_snippet": str(finding.get("code_snippet", ""))[:200],
                },
                scan_id=self.scan_id,
            )
            nodes.append(sink)
            entry = entry_by_file[file_path]
            edge = AttackEdge(
                edge_id=str(uuid.uuid4()),
                source_node_id=entry.node_id,
                target_node_id=sink.node_id,
                edge_type=EdgeType.REACHES_SINK,
                tainted=True,
                sanitized=False,
                call_site_file=file_path,
                call_site_line=int(finding.get("line_start") or 0),
                scan_id=self.scan_id,
            )
            edges.append(edge)

        for node in nodes:
            self.nx_graph.add_node(node.node_id, **node.to_dict())
        for edge in edges:
            self.nx_graph.add_edge(edge.source_node_id, edge.target_node_id, **edge.to_dict())

        if self.neo4j_uri and self.neo4j_password:
            try:
                await self._persist_to_neo4j(nodes, edges)
            except Exception as exc:
                logger.warning("Neo4j persist skipped: %s", exc)

        return nodes, edges

    async def _persist_to_neo4j(self, nodes: list[AttackNode], edges: list[AttackEdge]) -> None:
        from neo4j import AsyncGraphDatabase

        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )
        async with self._driver.session() as session:
            await session.run(
                "MATCH (n:AttackNode {scan_id: $scan_id}) DETACH DELETE n",
                scan_id=self.scan_id,
            )
            for node in nodes:
                data = node.to_dict()
                if node.is_crown_jewel:
                    await session.run(
                        """
                        MERGE (n:AttackNode {node_id: $node_id})
                        SET n = $props
                        SET n:CrownJewel
                        """,
                        node_id=node.node_id,
                        props=data,
                    )
                else:
                    await session.run(
                        """
                        MERGE (n:AttackNode {node_id: $node_id})
                        SET n = $props
                        """,
                        node_id=node.node_id,
                        props=data,
                    )
            for edge in edges:
                await session.run(
                    """
                    MATCH (src:AttackNode {node_id: $source})
                    MATCH (tgt:AttackNode {node_id: $target})
                    MERGE (src)-[r:REACHES_SINK {edge_id: $edge_id}]->(tgt)
                    SET r = $props
                    """,
                    source=edge.source_node_id,
                    target=edge.target_node_id,
                    edge_id=edge.edge_id,
                    props=edge.to_dict(),
                )

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    def _node_id(self, finding: dict[str, Any]) -> str:
        key = (
            f"{finding.get('file_path', '')}:"
            f"{finding.get('line_start', 0)}:"
            f"{finding.get('function_name', finding.get('name', ''))}"
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]
