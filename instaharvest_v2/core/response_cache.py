"""
Response Cache (LRU + TTL)
==========================
Thread-safe in-memory cache for API responses with LRU eviction and
per-entry TTL.

Design choices:
    - OrderedDict-based LRU: O(1) get/put/move-to-end.
    - Per-entry TTL: each cache_set() can override the default TTL.
    - Stale-while-revalidate (SWR): get_with_status() reports whether
      a returned value is fresh, stale, or missing — enabling background
      refresh patterns.
    - Pattern invalidation: invalidate by exact key, prefix, or regex.

Usage:
    cache = ResponseCache(maxsize=1000, default_ttl=300)

    key = cache_key("get_profile", "cristiano")
    value = cache.get(key)
    if value is None:
        value = expensive_call()
        cache.set(key, value, ttl=600)

    # Or with stale awareness:
    entry, status = cache.get_with_status(key)
    if status is CacheStatus.HIT:
        return entry.value
    if status is CacheStatus.STALE:
        background_refresh(key)
        return entry.value
    return None

    # Pattern invalidation
    cache.invalidate_prefix("get_profile:")
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("instaharvest_v2.core.response_cache")


class CacheStatus(str, Enum):
    """Result of a cache lookup."""

    MISS = "miss"      # Key not present
    HIT = "hit"        # Key present and fresh (within TTL)
    STALE = "stale"    # Key present but past TTL (kept for SWR)


@dataclass
class CacheEntry:
    """A single cached value with metadata."""

    value: Any
    created_at: float
    ttl: float                         # seconds; 0 = never expires
    hits: int = 0
    last_accessed_at: float = field(default_factory=time.time)

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        if self.ttl <= 0:
            return False
        return self.age > self.ttl

    def is_stale(self, stale_grace: float) -> bool:
        """Within `stale_grace` seconds past expiry — usable for SWR."""
        if self.ttl <= 0:
            return False
        age = self.age
        return self.ttl < age <= self.ttl + stale_grace


def cache_key(*parts: Any) -> str:
    """
    Deterministic cache key from arbitrary parts.

    Mixes positional args into a stable string. Dict/list values are
    JSON-serialized with sorted keys to keep equivalent inputs equal.

    Example:
        cache_key("get_profile", "cristiano", {"max_count": 12})
        # -> "get_profile:cristiano:c4a8f1b2..."
    """
    rendered = []
    for part in parts:
        if isinstance(part, (str, int, float, bool)) or part is None:
            rendered.append(str(part))
        else:
            try:
                serialized = json.dumps(
                    part, sort_keys=True, default=str, ensure_ascii=False,
                )
            except (TypeError, ValueError):
                serialized = repr(part)
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
            rendered.append(digest)
    return ":".join(rendered)


class ResponseCache:
    """
    Thread-safe LRU cache with per-entry TTL.

    Args:
        maxsize: Maximum number of entries. 0 = unlimited.
        default_ttl: Default TTL in seconds. 0 = entries never expire.
        stale_grace: Seconds past TTL during which entries are returned
            with STALE status (instead of MISS). Enables SWR.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        default_ttl: float = 300.0,
        stale_grace: float = 0.0,
    ):
        if maxsize < 0:
            raise ValueError("maxsize must be >= 0")
        if default_ttl < 0:
            raise ValueError("default_ttl must be >= 0")
        if stale_grace < 0:
            raise ValueError("stale_grace must be >= 0")

        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._stale_grace = stale_grace

        self._store: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._lock = threading.Lock()

        # Statistics
        self._hits: int = 0
        self._misses: int = 0
        self._stale_hits: int = 0
        self._evictions: int = 0
        self._expirations: int = 0
        self._sets: int = 0

    # ─── Lookup API ────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """
        Return the cached value for `key`, or None on miss/expired.
        Stale entries within `stale_grace` are NOT returned by `get()`;
        use `get_with_status()` to opt into SWR behavior.
        """
        entry, status = self.get_with_status(key)
        if status is CacheStatus.HIT:
            return entry.value
        return None

    def get_with_status(
        self, key: str,
    ) -> Tuple[Optional[CacheEntry], CacheStatus]:
        """
        Return (entry, status) tuple.
            status == HIT: entry is fresh.
            status == STALE: entry is past TTL but within stale_grace.
            status == MISS: nothing usable.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None, CacheStatus.MISS

            if entry.is_expired:
                if entry.is_stale(self._stale_grace):
                    self._stale_hits += 1
                    entry.hits += 1
                    entry.last_accessed_at = time.time()
                    self._store.move_to_end(key)
                    return entry, CacheStatus.STALE
                # Past stale_grace — drop and report miss
                del self._store[key]
                self._expirations += 1
                self._misses += 1
                return None, CacheStatus.MISS

            # Fresh hit
            self._hits += 1
            entry.hits += 1
            entry.last_accessed_at = time.time()
            self._store.move_to_end(key)
            return entry, CacheStatus.HIT

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[float] = None,
    ) -> Any:
        """
        Return cached value or, on miss, compute it via `factory()`,
        cache it, and return it.

        Note: `factory` is called OUTSIDE the cache lock so it may
        race with concurrent callers (last writer wins). Acceptable
        for idempotent reads.
        """
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl=ttl)
        return value

    # ─── Mutation API ──────────────────────────────────────

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
    ) -> None:
        """Store `value` under `key` with optional per-entry TTL."""
        effective_ttl = self._default_ttl if ttl is None else ttl
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl=effective_ttl,
        )
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = entry
            else:
                self._store[key] = entry
                self._sets += 1
                self._evict_if_needed()

    def delete(self, key: str) -> bool:
        """Remove `key`. Return True if it was present."""
        with self._lock:
            return self._store.pop(key, None) is not None

    def invalidate_prefix(self, prefix: str) -> int:
        """Delete every key starting with `prefix`. Return count removed."""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def invalidate_pattern(self, pattern: str) -> int:
        """Delete every key matching the regex `pattern`. Return count."""
        regex = re.compile(pattern)
        with self._lock:
            keys = [k for k in self._store if regex.search(k)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def clear(self) -> None:
        """Drop every entry."""
        with self._lock:
            self._store.clear()

    # ─── Introspection ─────────────────────────────────────

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            return entry is not None and not entry.is_expired

    @property
    def stats(self) -> Dict[str, Any]:
        """Snapshot of cache statistics."""
        with self._lock:
            total = self._hits + self._misses + self._stale_hits
            return {
                "size": len(self._store),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "stale_hits": self._stale_hits,
                "evictions": self._evictions,
                "expirations": self._expirations,
                "sets": self._sets,
                "hit_rate": (
                    (self._hits + self._stale_hits) / total
                    if total > 0 else 0.0
                ),
            }

    def cleanup_expired(self) -> int:
        """
        Eagerly drop every expired entry past the stale grace period.
        Returns the number of entries removed.

        Useful as a periodic maintenance task.
        """
        removed = 0
        with self._lock:
            keys = [
                k for k, entry in self._store.items()
                if entry.is_expired and not entry.is_stale(self._stale_grace)
            ]
            for k in keys:
                del self._store[k]
                self._expirations += 1
                removed += 1
        return removed

    # ─── Internal ──────────────────────────────────────────

    def _evict_if_needed(self) -> None:
        """LRU eviction. Caller must hold the lock."""
        if self._maxsize <= 0:
            return
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
            self._evictions += 1
