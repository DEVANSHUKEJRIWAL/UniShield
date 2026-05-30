"""Simple TTL cache for hot read endpoints (Week 8)."""

import time
from functools import wraps
from typing import Any, Callable


_cache: dict[str, tuple[float, Any]] = {}


def cached_ttl(seconds: int = 30) -> Callable:
    """Decorator caching async function results by args key."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = f"{fn.__name__}:{args}:{sorted(kwargs.items())}"
            now = time.time()
            hit = _cache.get(key)
            if hit and now - hit[0] < seconds:
                return hit[1]
            result = await fn(*args, **kwargs)
            _cache[key] = (now, result)
            return result

        return wrapper

    return decorator
