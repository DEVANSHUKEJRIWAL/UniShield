"""Attack path graph schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NodeType(str, Enum):
    ENTRY_POINT = "entry_point"
    FUNCTION = "function"
    CLASS = "class"
    SINK = "sink"
    CROWN_JEWEL = "crown_jewel"
    SANITIZER = "sanitizer"
    EXTERNAL_CALL = "external_call"
    SECRET = "secret"
    DATA_STORE = "data_store"


class EdgeType(str, Enum):
    CALLS = "calls"
    PASSES_DATA = "passes_data"
    REACHES_SINK = "reaches_sink"
    BYPASSES_CHECK = "bypasses_check"
    ACCESSES = "accesses"


class STRIDECategory(str, Enum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFO_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SVC = "denial_of_service"
    ELEVATION = "elevation_of_privilege"


@dataclass
class AttackNode:
    node_id: str
    node_type: NodeType
    name: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    is_crown_jewel: bool = False
    is_sanitizer: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    scan_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, NodeType) else self.node_type,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "language": self.language,
            "is_crown_jewel": self.is_crown_jewel,
            "is_sanitizer": self.is_sanitizer,
            "metadata": self.metadata,
            "scan_id": self.scan_id,
        }


@dataclass
class AttackEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    tainted: bool
    sanitized: bool
    call_site_file: str
    call_site_line: int
    scan_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value if isinstance(self.edge_type, EdgeType) else self.edge_type,
            "tainted": self.tainted,
            "sanitized": self.sanitized,
            "call_site_file": self.call_site_file,
            "call_site_line": self.call_site_line,
            "scan_id": self.scan_id,
        }


@dataclass
class AttackPath:
    path_id: str
    scan_id: str
    nodes: list[AttackNode]
    edges: list[AttackEdge]
    entry_point: AttackNode
    sink: AttackNode
    path_length: int
    has_sanitizer: bool
    risk_score: float
    exploitability: float
    stride_threats: list[STRIDECategory]
    reaches_crown_jewel: bool
    crown_jewel_name: Optional[str]
    description: str
    attack_narrative: str
    remediation: str


@dataclass
class Chokepoint:
    node: AttackNode
    paths_blocked: int
    blocking_score: float
    fix_effort: str
    recommended_fix: str


@dataclass
class BlastRadius:
    entry_point: AttackNode
    reachable_sinks: list[AttackNode]
    reachable_crown_jewels: list[str]
    total_paths: int
    max_path_depth: int
    blast_score: float
    worst_case_impact: str


@dataclass
class AttackPathOutput:
    scan_id: str
    total_nodes: int
    total_edges: int
    total_paths: int
    paths: list[AttackPath]
    chokepoints: list[Chokepoint]
    blast_radii: list[BlastRadius]
    graph_summary: dict[str, Any]
    neo4j_query_url: Optional[str]
    generated_at: str
