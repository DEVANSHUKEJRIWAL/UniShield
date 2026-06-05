"""Build attack path graph from SCR findings and AST call graphs."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Optional

import networkx as nx

from backend.attack_path.ast_extractor import ASTExtractor, ExtractedEntryPoint, FileAST
from backend.schemas.attack_path_schemas import AttackEdge, AttackNode, EdgeType, NodeType

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
    """Builds directed attack graph from AST entry points, call edges, and SCR findings."""

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
        self._extractor = ASTExtractor()

    async def build_from_scan_results(
        self,
        code_findings: list[dict[str, Any]],
        file_asts: dict[str, Any] | None = None,
        language_map: dict[str, str] | None = None,
        crown_jewels: list[str] | None = None,
        ioc_list: list[str] | None = None,
        file_contents: dict[str, str] | None = None,
    ) -> tuple[list[AttackNode], list[AttackEdge]]:
        crown_jewels = crown_jewels or []
        language_map = language_map or {}
        nodes: list[AttackNode] = []
        edges: list[AttackEdge] = []
        node_index: dict[str, AttackNode] = {}

        parsed_asts = self._normalize_file_asts(
            file_asts=file_asts,
            code_findings=code_findings,
            language_map=language_map,
            file_contents=file_contents,
        )

        for file_path, file_ast in parsed_asts.items():
            language = language_map.get(file_path, file_ast.language)
            for entry in file_ast.entry_points:
                node = self._entry_node(entry, language, crown_jewels)
                nodes.append(node)
                node_index[node.node_id] = node

            for fn in file_ast.functions:
                node = AttackNode(
                    node_id=self._node_id({"file_path": file_path, "name": fn.name, "line_start": fn.line_start}),
                    node_type=NodeType.FUNCTION,
                    name=fn.name,
                    file_path=file_path,
                    line_start=fn.line_start,
                    line_end=fn.line_end,
                    language=language,
                    is_crown_jewel=any(j in file_path for j in crown_jewels),
                    metadata={"parameters": fn.parameters, "calls": fn.calls},
                    scan_id=self.scan_id,
                )
                nodes.append(node)
                node_index[node.node_id] = node

            for sanitizer in file_ast.sanitizers:
                node = AttackNode(
                    node_id=self._node_id({"file_path": file_path, "name": sanitizer, "line_start": 0}),
                    node_type=NodeType.SANITIZER,
                    name=sanitizer,
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    language=language,
                    is_sanitizer=True,
                    scan_id=self.scan_id,
                )
                nodes.append(node)
                node_index[node.node_id] = node

            for edge in file_ast.call_edges:
                src_id = self._node_id({"file_path": file_path, "name": edge.caller, "line_start": 0})
                tgt_id = self._node_id({"file_path": file_path, "name": edge.callee, "line_start": 0})
                if src_id not in node_index or tgt_id not in node_index:
                    continue
                edges.append(
                    AttackEdge(
                        edge_id=str(uuid.uuid4()),
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        edge_type=EdgeType.CALLS,
                        tainted=bool(edge.tainted_args),
                        sanitized=False,
                        call_site_file=file_path,
                        call_site_line=edge.line,
                        scan_id=self.scan_id,
                    )
                )

            for entry in file_ast.entry_points:
                entry_id = self._node_id(
                    {"file_path": file_path, "name": entry.handler, "line_start": entry.line_start, "route": entry.route}
                )
                handler_id = self._node_id({"file_path": file_path, "name": entry.handler, "line_start": entry.line_start})
                if entry_id in node_index and handler_id in node_index and entry_id != handler_id:
                    edges.append(
                        AttackEdge(
                            edge_id=str(uuid.uuid4()),
                            source_node_id=entry_id,
                            target_node_id=handler_id,
                            edge_type=EdgeType.CALLS,
                            tainted=True,
                            sanitized=False,
                            call_site_file=file_path,
                            call_site_line=entry.line_start,
                            scan_id=self.scan_id,
                        )
                    )

            for sink_call in file_ast.sink_calls:
                sink = AttackNode(
                    node_id=self._node_id(
                        {
                            "file_path": file_path,
                            "name": sink_call.get("callee", "sink"),
                            "line_start": sink_call.get("line", 0),
                        }
                    ),
                    node_type=NodeType.SINK,
                    name=str(sink_call.get("callee", "sink")),
                    file_path=file_path,
                    line_start=int(sink_call.get("line") or 0),
                    line_end=int(sink_call.get("line") or 0),
                    language=language,
                    is_crown_jewel=any(j in file_path for j in crown_jewels),
                    metadata={"sink_type": sink_call.get("sink_type"), "source": "ast"},
                    scan_id=self.scan_id,
                )
                nodes.append(sink)
                node_index[sink.node_id] = sink
                handler_name = file_ast.functions[0].name if file_ast.functions else None
                if handler_name:
                    src_id = self._node_id({"file_path": file_path, "name": handler_name, "line_start": 0})
                    if src_id in node_index:
                        edges.append(
                            AttackEdge(
                                edge_id=str(uuid.uuid4()),
                                source_node_id=src_id,
                                target_node_id=sink.node_id,
                                edge_type=EdgeType.REACHES_SINK,
                                tainted=True,
                                sanitized=False,
                                call_site_file=file_path,
                                call_site_line=int(sink_call.get("line") or 0),
                                scan_id=self.scan_id,
                            )
                        )

        entry_by_file: dict[str, AttackNode] = {
            n.file_path: n for n in nodes if n.node_type == NodeType.ENTRY_POINT
        }

        for finding in code_findings:
            file_path = str(finding.get("file_path") or "unknown")
            category = str(finding.get("category", "unknown")).lower()
            if category not in SINK_CATEGORIES and "inject" not in category:
                continue

            if file_path not in entry_by_file:
                entry = AttackNode(
                    node_id=self._node_id({"file_path": file_path, "name": "entry", "line_start": 0}),
                    node_type=NodeType.ENTRY_POINT,
                    name=f"entry:{file_path}",
                    file_path=file_path,
                    line_start=1,
                    line_end=1,
                    language=language_map.get(file_path, str(finding.get("language", "unknown"))),
                    metadata={"route": file_path, "source": "finding_fallback"},
                    scan_id=self.scan_id,
                )
                entry_by_file[file_path] = entry
                nodes.append(entry)
                node_index[entry.node_id] = entry

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
                    "source": "finding",
                },
                scan_id=self.scan_id,
            )
            if sink.node_id not in node_index:
                nodes.append(sink)
                node_index[sink.node_id] = sink

            entry = entry_by_file[file_path]
            path_exists = nx.has_path(self.nx_graph, entry.node_id, sink.node_id) if self.nx_graph.number_of_nodes() else False
            if not path_exists:
                fn_name = str(finding.get("function_name") or "")
                fn_id = self._node_id({"file_path": file_path, "name": fn_name, "line_start": 0}) if fn_name else None
                if fn_id and fn_id in node_index:
                    edges.append(
                        AttackEdge(
                            edge_id=str(uuid.uuid4()),
                            source_node_id=entry.node_id,
                            target_node_id=fn_id,
                            edge_type=EdgeType.PASSES_DATA,
                            tainted=True,
                            sanitized=False,
                            call_site_file=file_path,
                            call_site_line=int(finding.get("line_start") or 0),
                            scan_id=self.scan_id,
                        )
                    )
                    edges.append(
                        AttackEdge(
                            edge_id=str(uuid.uuid4()),
                            source_node_id=fn_id,
                            target_node_id=sink.node_id,
                            edge_type=EdgeType.REACHES_SINK,
                            tainted=True,
                            sanitized=any(
                                s.file_path == file_path and s.is_sanitizer for s in nodes if s.node_type == NodeType.SANITIZER
                            ),
                            call_site_file=file_path,
                            call_site_line=int(finding.get("line_start") or 0),
                            scan_id=self.scan_id,
                        )
                    )
                else:
                    edges.append(
                        AttackEdge(
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
                    )

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

    def _normalize_file_asts(
        self,
        *,
        file_asts: dict[str, Any] | None,
        code_findings: list[dict[str, Any]],
        language_map: dict[str, str],
        file_contents: dict[str, str] | None,
    ) -> dict[str, FileAST]:
        if file_asts:
            parsed: dict[str, FileAST] = {}
            for file_path, payload in file_asts.items():
                if isinstance(payload, FileAST):
                    parsed[file_path] = payload
                elif isinstance(payload, dict):
                    parsed[file_path] = FileAST(
                        file_path=file_path,
                        language=payload.get("language", language_map.get(file_path, "python")),
                        entry_points=[
                            ExtractedEntryPoint(**ep) for ep in payload.get("entry_points", []) if isinstance(ep, dict)
                        ],
                        functions=[],
                        call_edges=[],
                        sanitizers=list(payload.get("sanitizers", [])),
                        sink_calls=list(payload.get("sink_calls", [])),
                    )
            if parsed:
                return parsed

        files = sorted({str(f.get("file_path")) for f in code_findings if f.get("file_path")})
        sources = self._extractor.build_sources_from_findings(files, code_findings, file_contents)
        return self._extractor.extract_many(sources, language_map)

    def _entry_node(self, entry: ExtractedEntryPoint, language: str, crown_jewels: list[str]) -> AttackNode:
        return AttackNode(
            node_id=self._node_id(
                {"file_path": entry.file_path, "name": entry.handler, "line_start": entry.line_start, "route": entry.route}
            ),
            node_type=NodeType.ENTRY_POINT,
            name=f"{entry.method} {entry.route}",
            file_path=entry.file_path,
            line_start=entry.line_start,
            line_end=entry.line_end,
            language=language,
            is_crown_jewel=any(j in entry.file_path for j in crown_jewels),
            metadata={
                "route": entry.route,
                "method": entry.method,
                "handler": entry.handler,
                "framework": entry.framework,
            },
            scan_id=self.scan_id,
        )

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
                rel_type = edge.edge_type.value.upper()
                await session.run(
                    f"""
                    MATCH (src:AttackNode {{node_id: $source}})
                    MATCH (tgt:AttackNode {{node_id: $target}})
                    MERGE (src)-[r:{rel_type} {{edge_id: $edge_id}}]->(tgt)
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
            f"{finding.get('function_name', finding.get('name', ''))}:"
            f"{finding.get('route', '')}"
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]
