"""Prometheus metrics middleware (Week 10)."""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

REQUEST_COUNT = Counter(
    "unishield_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)
REQUEST_LATENCY = Histogram(
    "unishield_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
)
AGENT_FINDINGS = Counter(
    "unishield_agent_findings_total",
    "Findings emitted by agents",
    ["agent", "severity"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record request metrics and dual-write latency to TimescaleDB."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        route = request.url.path
        REQUEST_COUNT.labels(request.method, route, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, route).observe(elapsed_ms / 1000)
        try:
            from packages.core.metrics_db import record_api_latency

            await record_api_latency(route, request.method, elapsed_ms, response.status_code)
        except Exception:
            pass
        return response


def metrics_endpoint() -> StarletteResponse:
    """Expose Prometheus scrape endpoint."""
    return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
