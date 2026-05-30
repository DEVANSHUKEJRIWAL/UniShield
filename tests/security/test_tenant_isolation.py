"""Tenant isolation boundary tests — scaffolded for Week 5."""

import pytest


@pytest.mark.skip(reason="Full tenant isolation in Week 5")
def test_cross_tenant_data_access_denied() -> None:
    """Cross-tenant data access returns 403."""
    pass


@pytest.mark.skip(reason="Full tenant isolation in Week 5")
def test_neo4j_query_includes_tenant_filter() -> None:
    """All Neo4j queries include clientId filter."""
    pass
