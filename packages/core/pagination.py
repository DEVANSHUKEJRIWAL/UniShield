"""Pagination helpers (Week 5)."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated API response."""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 1


def paginate(total: int, page: int, page_size: int) -> dict[str, int]:
    """Return pagination metadata."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    pages = max(1, (total + page_size - 1) // page_size)
    return {"page": page, "page_size": page_size, "pages": pages, "offset": (page - 1) * page_size}
