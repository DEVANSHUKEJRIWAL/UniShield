"""RBAC boundary tests — scaffolded for Week 5."""

import pytest


@pytest.mark.skip(reason="Full RBAC enforcement in Week 5")
def test_platform_admin_cross_tenant_access() -> None:
    """PLATFORM_ADMIN can access cross-tenant data."""
    pass


@pytest.mark.skip(reason="Full RBAC enforcement in Week 5")
def test_soc_analyst_readonly_board_restriction() -> None:
    """READONLY_BOARD cannot access alert management."""
    pass
