"""Facade for running attack path analysis on SCR findings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from unishield.attack_path.attack_path_output import AttackPathOutputSerializer
from unishield.attack_path.graph_builder import AttackPathGraphBuilder
from unishield.attack_path.path_analyzer import AttackPathAnalyzer
from unishield.attack_path.stride_analyzer import STRIDEAnalyzer
from unishield.config.settings import Settings, settings
from unishield.schemas.attack_path_schemas import AttackPathOutput, NodeType


class AttackPathService:
    """Runs graph build + path analysis for a SCR scan."""

    def __init__(self, app_settings: Settings | None = None, model_router: Any | None = None) -> None:
        self.settings = app_settings or settings
        self.model_router = model_router

    async def analyze(
        self,
        scan_id: str,
        code_findings: list[dict[str, Any]],
        crown_jewels: list[str] | None = None,
        language_map: dict[str, str] | None = None,
        ioc_list: list[str] | None = None,
    ) -> AttackPathOutput:
        builder = AttackPathGraphBuilder(
            scan_id=scan_id,
            neo4j_uri=self.settings.neo4j_uri if self.settings.neo4j_password else None,
            neo4j_user=self.settings.neo4j_user,
            neo4j_password=self.settings.neo4j_password,
        )
        nodes, edges = await builder.build_from_scan_results(
            code_findings=[f if isinstance(f, dict) else f.model_dump() for f in code_findings],
            language_map=language_map or {},
            crown_jewels=crown_jewels or [],
            ioc_list=ioc_list or [],
        )
        await builder.close()

        analyzer = AttackPathAnalyzer(builder.nx_graph, scan_id, model_router=self.model_router)
        paths = await analyzer.find_all_paths(max_depth=15, limit=100)
        paths = STRIDEAnalyzer().analyze_all(paths)
        chokepoints = await analyzer.find_chokepoints(paths)
        entry_points = [n for n in nodes if n.node_type == NodeType.ENTRY_POINT]
        blast_radii = await analyzer.compute_blast_radii(entry_points, paths)

        output = AttackPathOutput(
            scan_id=scan_id,
            total_nodes=len(nodes),
            total_edges=len(edges),
            total_paths=len(paths),
            paths=paths[:50],
            chokepoints=chokepoints,
            blast_radii=blast_radii,
            graph_summary={
                "entry_points": sum(1 for n in nodes if n.node_type == NodeType.ENTRY_POINT),
                "sinks": sum(1 for n in nodes if n.node_type == NodeType.SINK),
                "crown_jewel_paths": sum(1 for p in paths if p.reaches_crown_jewel),
            },
            neo4j_query_url=(
                f"{self.settings.neo4j_browser_url}?query="
                f"MATCH (n:AttackNode {{scan_id:'{scan_id}'}}) RETURN n LIMIT 200"
                if self.settings.neo4j_password
                else None
            ),
            generated_at=datetime.now(UTC).isoformat(),
        )
        return output

    @staticmethod
    def to_shared_memory_summary(output: AttackPathOutput) -> dict[str, Any]:
        return AttackPathOutputSerializer.summary(output)
