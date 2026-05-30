"""Tenant isolation tests."""

from packages.core.auth import require_tenant_access
from packages.shared_types.constants import UserRole


def test_soc_analyst_same_tenant() -> None:
    """SOC analyst can access own tenant."""
    assert require_tenant_access("meridian-financial", "meridian-financial", UserRole.SOC_ANALYST)


def test_soc_analyst_cross_tenant_denied() -> None:
    """SOC analyst cannot access other tenant."""
    assert not require_tenant_access("meridian-financial", "aerodyne-corp", UserRole.SOC_ANALYST)


def test_platform_admin_cross_tenant() -> None:
    """Platform admin can access any tenant."""
    assert require_tenant_access("meridian-financial", "aerodyne-corp", UserRole.PLATFORM_ADMIN)
