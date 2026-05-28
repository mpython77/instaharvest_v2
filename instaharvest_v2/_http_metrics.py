"""
HTTP Metrics
============
Pre-declared metric instances used by HttpClient and AsyncHttpClient.

Centralizing the declarations ensures that:
    - Metric names stay consistent across sync and async clients.
    - Labels stay disciplined (no cardinality explosion from per-user_id).
    - Anyone can introspect what metrics this library exposes by reading
      this single file.

Exposed metrics:

    instaharvest_http_requests_total           Counter   {method, endpoint, outcome}
    instaharvest_http_request_duration_seconds Histogram {method, endpoint}
    instaharvest_http_errors_total             Counter   {method, endpoint, error_type}
    instaharvest_http_retries_total            Counter   {endpoint, reason}
    instaharvest_circuit_short_circuits_total  Counter   {endpoint}

Inspection:
    from instaharvest_v2.core import metrics
    print(metrics.snapshot())
    print(metrics.export_prometheus())
"""

from .core.metrics import metrics


# ─── Counter: total requests, by outcome ───────────────────
HTTP_REQUESTS_TOTAL = metrics.counter(
    "instaharvest_http_requests_total",
    description="Total HTTP requests sent, labeled by method, endpoint, and outcome",
)

# ─── Histogram: per-request duration ───────────────────────
HTTP_REQUEST_DURATION = metrics.histogram(
    "instaharvest_http_request_duration_seconds",
    description="HTTP request duration in seconds",
)

# ─── Counter: errors by type ───────────────────────────────
HTTP_ERRORS_TOTAL = metrics.counter(
    "instaharvest_http_errors_total",
    description="Total HTTP errors, labeled by method, endpoint, and error_type",
)

# ─── Counter: retry attempts ───────────────────────────────
HTTP_RETRIES_TOTAL = metrics.counter(
    "instaharvest_http_retries_total",
    description="Total retry attempts triggered, labeled by endpoint and reason",
)

# ─── Counter: short-circuits (open breaker rejected a call) ─
HTTP_SHORT_CIRCUITS_TOTAL = metrics.counter(
    "instaharvest_http_short_circuits_total",
    description="Calls rejected by an OPEN circuit breaker (fail-fast)",
)


def record_request(
    method: str,
    endpoint: str,
    outcome: str,
    duration_seconds: float,
    error_type: str = "",
) -> None:
    """
    Record a single completed request.

    Args:
        method: HTTP method (GET, POST, ...).
        endpoint: Normalized endpoint key (use _endpoint_keys.endpoint_key).
        outcome: "success" | "error".
        duration_seconds: How long the call took.
        error_type: Exception class name (e.g., "RateLimitError"). Empty if success.
    """
    base_labels = {"method": method, "endpoint": endpoint}

    HTTP_REQUESTS_TOTAL.inc(labels={**base_labels, "outcome": outcome})
    HTTP_REQUEST_DURATION.observe(duration_seconds, labels=base_labels)

    if outcome != "success" and error_type:
        HTTP_ERRORS_TOTAL.inc(
            labels={**base_labels, "error_type": error_type},
        )


def record_retry(endpoint: str, reason: str) -> None:
    """Record a retry attempt for an endpoint."""
    HTTP_RETRIES_TOTAL.inc(labels={"endpoint": endpoint, "reason": reason})


def record_short_circuit(endpoint: str) -> None:
    """Record a request rejected by an open circuit breaker."""
    HTTP_SHORT_CIRCUITS_TOTAL.inc(labels={"endpoint": endpoint})
