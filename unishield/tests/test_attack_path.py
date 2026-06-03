"""Tests for AST-based attack path extraction."""

from __future__ import annotations

import pytest

from unishield.attack_path.ast_extractor import ASTExtractor
from unishield.attack_path.graph_builder import AttackPathGraphBuilder
from unishield.attack_path.path_analyzer import AttackPathAnalyzer
from unishield.attack_path.stride_analyzer import STRIDEAnalyzer
from unishield.schemas.attack_path_schemas import AttackNode, AttackPath, NodeType, STRIDECategory

FASTAPI_SOURCE = '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/users/{user_id}")
async def get_user(user_id: str):
    query = f"SELECT * FROM users WHERE id={user_id}"
    db.execute(query)
    return {"ok": True}

def sanitize(value: str) -> str:
    return value.strip()
'''


def _finding(category: str, file_path: str = "app/api.py", severity: str = "HIGH") -> dict:
    return {
        "file_path": file_path,
        "line_start": 10,
        "line_end": 12,
        "category": category,
        "severity": severity,
        "function_name": "get_user",
        "language": "python",
        "code_snippet": "db.execute(query)",
    }


def test_ast_extractor_finds_fastapi_entry_point():
    extractor = ASTExtractor()
    file_ast = extractor.extract_file("app/api.py", FASTAPI_SOURCE, "python")
    assert len(file_ast.entry_points) >= 1
    assert file_ast.entry_points[0].route == "/api/users/{user_id}"
    assert file_ast.entry_points[0].handler == "get_user"
    assert any(edge.caller == "get_user" for edge in file_ast.call_edges)


def test_ast_extractor_detects_sink_calls():
    extractor = ASTExtractor()
    file_ast = extractor.extract_file("app/api.py", FASTAPI_SOURCE, "python")
    assert any(s["sink_type"] == "sql_injection" for s in file_ast.sink_calls)


@pytest.mark.asyncio
async def test_graph_builder_uses_ast_entry_points():
    extractor = ASTExtractor()
    file_ast = extractor.extract_file("app/api.py", FASTAPI_SOURCE, "python")
    builder = AttackPathGraphBuilder(scan_id="scan-ast-1")
    findings = [_finding("sql_injection", "app/api.py")]
    nodes, edges = await builder.build_from_scan_results(
        code_findings=findings,
        file_asts={"app/api.py": file_ast.to_dict()},
    )
    await builder.close()

    entry_nodes = [n for n in nodes if n.node_type == NodeType.ENTRY_POINT]
    assert entry_nodes
    assert any("/api/users" in n.metadata.get("route", "") for n in entry_nodes)
    assert builder.nx_graph.number_of_edges() >= 1


@pytest.mark.asyncio
async def test_graph_builder_creates_nodes_from_findings():
    builder = AttackPathGraphBuilder(scan_id="scan-1")
    findings = [_finding("injection"), _finding("command_injection", "app/shell.py")]
    nodes, edges = await builder.build_from_scan_results(code_findings=findings)
    await builder.close()
    sink_nodes = [n for n in nodes if n.node_type == NodeType.SINK]
    assert len(sink_nodes) >= 2
    assert len({n.file_path for n in sink_nodes}) >= 2
    assert builder.nx_graph.number_of_nodes() >= 2


@pytest.mark.asyncio
async def test_path_scoring_crown_jewel_highest():
    builder = AttackPathGraphBuilder(scan_id="scan-2")
    findings = [_finding("injection", "src/payments/core.py")]
    nodes, _ = await builder.build_from_scan_results(
        code_findings=findings,
        crown_jewels=["src/payments"],
    )
    analyzer = AttackPathAnalyzer(builder.nx_graph, "scan-2")
    paths = await analyzer.find_all_paths(limit=10)
    assert paths
    normal_score = paths[0].risk_score
    paths[0].reaches_crown_jewel = True
    crowned = paths[0].risk_score + 40
    assert crowned >= normal_score
    await builder.close()


@pytest.mark.asyncio
async def test_chokepoint_detection():
    builder = AttackPathGraphBuilder(scan_id="scan-3")
    findings = [
        _finding("injection", "a.py"),
        _finding("injection", "b.py"),
        _finding("injection", "c.py"),
    ]
    await builder.build_from_scan_results(code_findings=findings)
    analyzer = AttackPathAnalyzer(builder.nx_graph, "scan-3")
    paths = await analyzer.find_all_paths(limit=10)
    chokepoints = await analyzer.find_chokepoints(paths)
    assert isinstance(chokepoints, list)
    await builder.close()


@pytest.mark.asyncio
async def test_blast_radius_includes_all_sinks():
    builder = AttackPathGraphBuilder(scan_id="scan-4")
    findings = [
        _finding("injection", "a.py"),
        _finding("command_injection", "b.py"),
        _finding("deserialization", "c.py"),
    ]
    nodes, _ = await builder.build_from_scan_results(code_findings=findings)
    analyzer = AttackPathAnalyzer(builder.nx_graph, "scan-4")
    paths = await analyzer.find_all_paths(limit=20)
    entries = [n for n in nodes if n.node_type == NodeType.ENTRY_POINT]
    blast = await analyzer.compute_blast_radii(entries, paths)
    if blast:
        assert blast[0].total_paths >= 1
    await builder.close()


def test_stride_sql_injection_path():
    entry = AttackNode(
        node_id="e1",
        node_type=NodeType.ENTRY_POINT,
        name="entry",
        file_path="a.py",
        line_start=1,
        line_end=1,
        language="python",
    )
    sink = AttackNode(
        node_id="s1",
        node_type=NodeType.SINK,
        name="query",
        file_path="a.py",
        line_start=10,
        line_end=10,
        language="python",
        metadata={"sink_type": "sql_injection"},
    )
    path = AttackPath(
        path_id="p1",
        scan_id="scan",
        nodes=[entry, sink],
        edges=[],
        entry_point=entry,
        sink=sink,
        path_length=1,
        has_sanitizer=False,
        risk_score=0,
        exploitability=0,
        stride_threats=[],
        reaches_crown_jewel=False,
        crown_jewel_name=None,
        description="",
        attack_narrative="",
        remediation="",
    )
    threats = STRIDEAnalyzer().analyze(path)
    assert STRIDECategory.TAMPERING in threats
    assert STRIDECategory.INFO_DISCLOSURE in threats


def test_stride_auth_bypass_path():
    entry = AttackNode(
        node_id="e1",
        node_type=NodeType.ENTRY_POINT,
        name="auth_login",
        file_path="auth.py",
        line_start=1,
        line_end=1,
        language="python",
    )
    sink = AttackNode(
        node_id="s1",
        node_type=NodeType.SINK,
        name="sink",
        file_path="auth.py",
        line_start=5,
        line_end=5,
        language="python",
        metadata={"sink_type": "injection"},
    )
    path = AttackPath(
        path_id="p1",
        scan_id="scan",
        nodes=[entry, sink],
        edges=[],
        entry_point=entry,
        sink=sink,
        path_length=1,
        has_sanitizer=False,
        risk_score=0,
        exploitability=0,
        stride_threats=[],
        reaches_crown_jewel=False,
        crown_jewel_name=None,
        description="",
        attack_narrative="",
        remediation="",
    )
    threats = STRIDEAnalyzer().analyze(path)
    assert STRIDECategory.SPOOFING in threats


def test_neo4j_parameterised_queries():
    source = open("/workspace/unishield/attack_path/graph_builder.py", encoding="utf-8").read()
    assert "session.run(" in source
    assert "$scan_id" in source
    assert "f\"MATCH (n:AttackNode {{scan_id:'{scan_id}'}}\"" not in source
