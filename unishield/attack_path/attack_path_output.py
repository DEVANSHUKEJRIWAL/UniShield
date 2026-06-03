"""Serialize attack path output for APIs and shared memory."""

from __future__ import annotations

from typing import Any

from unishield.schemas.attack_path_schemas import (
    AttackPath,
    AttackPathOutput,
    BlastRadius,
    Chokepoint,
    STRIDECategory,
)


class AttackPathOutputSerializer:
    """Convert attack path dataclasses to JSON-safe dicts."""

    @staticmethod
    def to_dict(output: AttackPathOutput) -> dict[str, Any]:
        return {
            "scan_id": output.scan_id,
            "total_nodes": output.total_nodes,
            "total_edges": output.total_edges,
            "total_paths": output.total_paths,
            "paths": [AttackPathOutputSerializer._path(p) for p in output.paths],
            "chokepoints": [AttackPathOutputSerializer._chokepoint(c) for c in output.chokepoints],
            "blast_radii": [AttackPathOutputSerializer._blast(b) for b in output.blast_radii],
            "graph_summary": output.graph_summary,
            "neo4j_query_url": output.neo4j_query_url,
            "generated_at": output.generated_at,
        }

    @staticmethod
    def summary(output: AttackPathOutput) -> dict[str, Any]:
        return {
            "total_paths": output.total_paths,
            "crown_jewel_paths": output.graph_summary.get("crown_jewel_paths", 0),
            "top_chokepoint": output.chokepoints[0].node.name if output.chokepoints else None,
            "highest_blast_score": output.blast_radii[0].blast_score if output.blast_radii else 0,
        }

    @staticmethod
    def _path(path: AttackPath) -> dict[str, Any]:
        return {
            "path_id": path.path_id,
            "scan_id": path.scan_id,
            "path_length": path.path_length,
            "has_sanitizer": path.has_sanitizer,
            "risk_score": path.risk_score,
            "exploitability": path.exploitability,
            "stride_threats": [t.value for t in path.stride_threats],
            "reaches_crown_jewel": path.reaches_crown_jewel,
            "crown_jewel_name": path.crown_jewel_name,
            "description": path.description,
            "attack_narrative": path.attack_narrative,
            "remediation": path.remediation,
            "entry_point": path.entry_point.to_dict(),
            "sink": path.sink.to_dict(),
        }

    @staticmethod
    def _chokepoint(item: Chokepoint) -> dict[str, Any]:
        return {
            "node": item.node.to_dict(),
            "paths_blocked": item.paths_blocked,
            "blocking_score": item.blocking_score,
            "fix_effort": item.fix_effort,
            "recommended_fix": item.recommended_fix,
        }

    @staticmethod
    def _blast(item: BlastRadius) -> dict[str, Any]:
        return {
            "entry_point": item.entry_point.to_dict(),
            "reachable_sinks": [s.to_dict() for s in item.reachable_sinks],
            "reachable_crown_jewels": item.reachable_crown_jewels,
            "total_paths": item.total_paths,
            "max_path_depth": item.max_path_depth,
            "blast_score": item.blast_score,
            "worst_case_impact": item.worst_case_impact,
        }
