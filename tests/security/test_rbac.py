"""RBAC and auth unit tests."""

from packages.core.auth import has_permission, require_tenant_access, hash_password, verify_password
from packages.shared_types.constants import UserRole


def test_password_hash_and_verify() -> None:
    """Password hashing works."""
    h = hash_password("test123")
    assert verify_password("test123", h)
    assert not verify_password("wrong", h)


def test_platform_admin_has_all_permissions() -> None:
    """PLATFORM_ADMIN has wildcard access."""
    assert has_permission(UserRole.PLATFORM_ADMIN, "read:alerts")
    assert has_permission(UserRole.PLATFORM_ADMIN, "admin:tenant")


def test_readonly_board_restricted() -> None:
    """READONLY_BOARD cannot write alerts."""
    assert has_permission(UserRole.READONLY_BOARD, "read:dashboard")
    assert not has_permission(UserRole.READONLY_BOARD, "write:alerts")


def test_tenant_isolation() -> None:
    """Cross-tenant access denied for non-admin."""
    assert require_tenant_access("tenant-a", "tenant-a", UserRole.SOC_ANALYST)
    assert not require_tenant_access("tenant-a", "tenant-b", UserRole.SOC_ANALYST)
    assert require_tenant_access("tenant-a", "tenant-b", UserRole.PLATFORM_ADMIN)
