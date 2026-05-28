"""
InstaHarvest v2 — Core Infrastructure
======================================
Enterprise-grade foundational components shared across HTTP clients,
API modules, and the agent system.

Components:
    - CircuitBreaker      : Three-state failure isolation (CLOSED/OPEN/HALF_OPEN)
    - TokenBucketLimiter  : O(1) rate limiting with burst capacity
    - ResponseCache       : LRU + TTL cache with thread-safe operations
    - ConnectionPool      : curl_cffi session pooling (sync + async)
    - Metrics             : Prometheus-compatible counters/gauges/histograms
    - StructuredLogger    : JSON log entries with correlation IDs

Design principles:
    1. Zero external runtime dependencies (stdlib only inside core/)
    2. Thread-safe AND async-safe — every primitive uses appropriate locks
    3. Observable — every operation emits metrics
    4. Composable — components can be used independently
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    CircuitBreakerRegistry,
)
from .token_bucket import (
    TokenBucketLimiter,
    AsyncTokenBucketLimiter,
    BucketConfig,
)
from .response_cache import (
    ResponseCache,
    CacheEntry,
    cache_key,
)
from .connection_pool import (
    ConnectionPool,
    AsyncConnectionPool,
    PoolConfig,
)
from .metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    metrics,
)
from .structured_logging import (
    StructuredLogger,
    LogContext,
    correlation_id,
)

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "CircuitBreakerRegistry",
    # Rate limiting
    "TokenBucketLimiter",
    "AsyncTokenBucketLimiter",
    "BucketConfig",
    # Caching
    "ResponseCache",
    "CacheEntry",
    "cache_key",
    # Connection pooling
    "ConnectionPool",
    "AsyncConnectionPool",
    "PoolConfig",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "metrics",
    # Logging
    "StructuredLogger",
    "LogContext",
    "correlation_id",
]
