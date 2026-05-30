"""Knowledge graph sync tests."""

import pytest

from services.knowledge_graph.service import KnowledgeGraphService


@pytest.mark.asyncio
async def test_write_finding_no_crash():
    svc = KnowledgeGraphService()
    await svc.write_finding(
        {
            "tenant_id": "meridian-financial",
            "finding_id": "test-finding-1",
            "title": "Test finding",
            "severity": "high",
            "agent_id": "test-agent",
            "evidence_references": ["db-prod-01"],
        }
    )


@pytest.mark.asyncio
async def test_traverse_paths_returns_structure():
    svc = KnowledgeGraphService()
    result = await svc.traverse_paths("workstation-42", "meridian-financial", depth=3)
    assert "paths" in result
    assert result["source"] == "workstation-42"
