"""
Token Bucket Rate Limiter
==========================
O(1) rate limiting algorithm replacing the O(n) sliding-window deque scan.

Algorithm:
    A bucket holds up to `capacity` tokens. Tokens refill continuously at
    `refill_rate` per second. Every request consumes 1 token. If the bucket
    is empty, the request waits until a token becomes available.

Why token bucket:
    - O(1) per acquire (no list scans)
    - Allows bursts up to `capacity` (real users hit endpoints in bursts)
    - Smooth refill (no thundering herd at window boundaries)
    - Same primitive works for sync and async

Usage:
    # Sync
    limiter = TokenBucketLimiter(BucketConfig(rate=5.0, capacity=10))
    limiter.acquire()  # blocks until a token is available

    # Async
    limiter = AsyncTokenBucketLimiter(BucketConfig(rate=5.0, capacity=10))
    await limiter.acquire()

    # Per-category limits (multiple buckets sharing one limiter)
    limiter = TokenBucketLimiter(default_config=BucketConfig(rate=5, capacity=10))
    limiter.acquire("get_profile")
    limiter.acquire("post_like", config=BucketConfig(rate=1, capacity=3))
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("instaharvest_v2.core.token_bucket")


@dataclass(frozen=True)
class BucketConfig:
    """
    Configuration for a single token bucket.

    Args:
        rate: Tokens generated per second (refill rate).
        capacity: Maximum tokens that can be held at once (burst size).
        max_wait: Maximum time to wait for a token (seconds).
            If exceeded, acquire() raises TimeoutError.
            None = wait indefinitely.
    """

    rate: float
    capacity: int
    max_wait: Optional[float] = None

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError("rate must be > 0")
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")


class _Bucket:
    """
    Internal bucket state. Not thread-safe by itself; the surrounding
    limiter holds the lock.
    """

    __slots__ = ("config", "tokens", "last_refill")

    def __init__(self, config: BucketConfig):
        self.config = config
        self.tokens: float = float(config.capacity)
        self.last_refill: float = time.monotonic()

    def refill(self, now: float) -> None:
        """Add accrued tokens since the last refill, capped at capacity."""
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        added = elapsed * self.config.rate
        self.tokens = min(float(self.config.capacity), self.tokens + added)
        self.last_refill = now

    def time_until_available(self, now: float) -> float:
        """Seconds until at least 1 token is available."""
        self.refill(now)
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.config.rate


class TokenBucketLimiter:
    """
    Thread-safe synchronous token bucket limiter.

    Supports either a single bucket (one global limit) or many named
    buckets (per-category limits).
    """

    def __init__(
        self,
        default_config: Optional[BucketConfig] = None,
        category_configs: Optional[Dict[str, BucketConfig]] = None,
    ):
        self._default_config = default_config or BucketConfig(rate=10.0, capacity=20)
        self._category_configs: Dict[str, BucketConfig] = dict(category_configs or {})
        self._buckets: Dict[str, _Bucket] = {}
        self._cond = threading.Condition()

    # ─── Public API ────────────────────────────────────────

    def acquire(
        self,
        category: str = "_default",
        config: Optional[BucketConfig] = None,
    ) -> None:
        """
        Block until a token is available, then consume it.

        Args:
            category: Bucket name. Each category has an independent bucket.
            config: Override config for this category (only used the first
                time the category is seen).

        Raises:
            TimeoutError: If `max_wait` is set and exceeded.
        """
        bucket = self._get_or_create_bucket(category, config)
        max_wait = bucket.config.max_wait
        deadline = time.monotonic() + max_wait if max_wait is not None else None

        with self._cond:
            while True:
                now = time.monotonic()
                wait_time = bucket.time_until_available(now)
                if wait_time <= 0:
                    bucket.tokens -= 1.0
                    return

                if deadline is not None:
                    remaining = deadline - now
                    if remaining <= 0:
                        raise TimeoutError(
                            f"TokenBucketLimiter timeout after {max_wait}s "
                            f"(category={category})"
                        )
                    wait_time = min(wait_time, remaining)

                self._cond.wait(timeout=wait_time)

    def try_acquire(
        self,
        category: str = "_default",
        config: Optional[BucketConfig] = None,
    ) -> bool:
        """
        Non-blocking. Return True if a token was consumed, False otherwise.
        """
        bucket = self._get_or_create_bucket(category, config)
        with self._cond:
            now = time.monotonic()
            bucket.refill(now)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def remaining(self, category: str = "_default") -> float:
        """Current token count for `category`."""
        with self._cond:
            bucket = self._buckets.get(category)
            if bucket is None:
                return float(
                    self._category_configs.get(category, self._default_config).capacity
                )
            bucket.refill(time.monotonic())
            return bucket.tokens

    def reset(self, category: Optional[str] = None) -> None:
        """Refill bucket(s) to full capacity."""
        with self._cond:
            if category is None:
                for bucket in self._buckets.values():
                    bucket.tokens = float(bucket.config.capacity)
                    bucket.last_refill = time.monotonic()
            elif category in self._buckets:
                bucket = self._buckets[category]
                bucket.tokens = float(bucket.config.capacity)
                bucket.last_refill = time.monotonic()
            self._cond.notify_all()

    # ─── Internal ──────────────────────────────────────────

    def _get_or_create_bucket(
        self,
        category: str,
        config: Optional[BucketConfig],
    ) -> _Bucket:
        with self._cond:
            bucket = self._buckets.get(category)
            if bucket is None:
                cfg = (
                    config
                    or self._category_configs.get(category)
                    or self._default_config
                )
                bucket = _Bucket(cfg)
                self._buckets[category] = bucket
            return bucket


class AsyncTokenBucketLimiter:
    """
    Async equivalent of TokenBucketLimiter.

    Uses asyncio.Condition for cooperative waiting. The bucket math is
    identical to the sync variant.

    Each running event loop should have its own instance — the internal
    Condition is bound to a specific loop on first use.
    """

    def __init__(
        self,
        default_config: Optional[BucketConfig] = None,
        category_configs: Optional[Dict[str, BucketConfig]] = None,
    ):
        self._default_config = default_config or BucketConfig(rate=10.0, capacity=20)
        self._category_configs: Dict[str, BucketConfig] = dict(category_configs or {})
        self._buckets: Dict[str, _Bucket] = {}
        self._cond: Optional[asyncio.Condition] = None
        self._init_lock = threading.Lock()

    def _ensure_cond(self) -> asyncio.Condition:
        if self._cond is None:
            with self._init_lock:
                if self._cond is None:
                    self._cond = asyncio.Condition()
        return self._cond

    async def acquire(
        self,
        category: str = "_default",
        config: Optional[BucketConfig] = None,
    ) -> None:
        bucket = self._get_or_create_bucket(category, config)
        cond = self._ensure_cond()
        max_wait = bucket.config.max_wait
        deadline = (
            asyncio.get_event_loop().time() + max_wait
            if max_wait is not None else None
        )

        async with cond:
            while True:
                now = time.monotonic()
                wait_time = bucket.time_until_available(now)
                if wait_time <= 0:
                    bucket.tokens -= 1.0
                    cond.notify()
                    return

                if deadline is not None:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        raise TimeoutError(
                            f"AsyncTokenBucketLimiter timeout after {max_wait}s "
                            f"(category={category})"
                        )
                    wait_time = min(wait_time, remaining)

                try:
                    await asyncio.wait_for(cond.wait(), timeout=wait_time)
                except asyncio.TimeoutError:
                    # Timeout on cond.wait() is a normal wakeup, not a hard timeout
                    continue

    async def try_acquire(
        self,
        category: str = "_default",
        config: Optional[BucketConfig] = None,
    ) -> bool:
        bucket = self._get_or_create_bucket(category, config)
        cond = self._ensure_cond()
        async with cond:
            now = time.monotonic()
            bucket.refill(now)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    async def remaining(self, category: str = "_default") -> float:
        cond = self._ensure_cond()
        async with cond:
            bucket = self._buckets.get(category)
            if bucket is None:
                return float(
                    self._category_configs.get(category, self._default_config).capacity
                )
            bucket.refill(time.monotonic())
            return bucket.tokens

    async def reset(self, category: Optional[str] = None) -> None:
        cond = self._ensure_cond()
        async with cond:
            if category is None:
                for bucket in self._buckets.values():
                    bucket.tokens = float(bucket.config.capacity)
                    bucket.last_refill = time.monotonic()
            elif category in self._buckets:
                bucket = self._buckets[category]
                bucket.tokens = float(bucket.config.capacity)
                bucket.last_refill = time.monotonic()
            cond.notify_all()

    def _get_or_create_bucket(
        self,
        category: str,
        config: Optional[BucketConfig],
    ) -> _Bucket:
        bucket = self._buckets.get(category)
        if bucket is None:
            cfg = (
                config
                or self._category_configs.get(category)
                or self._default_config
            )
            bucket = _Bucket(cfg)
            self._buckets[category] = bucket
        return bucket
