"""Tests for AST extractor."""

from __future__ import annotations

from unishield.attack_path.ast_extractor import ASTExtractor

SAMPLE = '''
from fastapi import APIRouter
router = APIRouter()

@router.post("/login")
async def login(request):
    user = request.json.get("user")
    db.execute(f"SELECT * FROM users WHERE name={user}")
    return {"ok": True}

def helper(data):
    os.system(data)
'''


def test_extract_entry_points_and_sinks():
    extractor = ASTExtractor()
    file_ast = extractor.extract_file("routes/auth.py", SAMPLE, "python")
    assert any(ep.route == "/login" for ep in file_ast.entry_points)
    assert any(s["sink_type"] == "sql_injection" for s in file_ast.sink_calls)
    assert any(edge.caller == "login" for edge in file_ast.call_edges)


def test_build_sources_from_findings():
    extractor = ASTExtractor()
    findings = [
        {
            "file_path": "app/api.py",
            "code_snippet": "db.execute(query)",
            "category": "injection",
        }
    ]
    sources = extractor.build_sources_from_findings(["app/api.py"], findings)
    assert "app/api.py" in sources
    assert "execute" in sources["app/api.py"]
