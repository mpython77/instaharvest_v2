"""
Connection Pool
================
curl_cffi session pooling with health tracking and automatic recycling.

Why pool sessions:
    Creating a curl_cffi.Session establishes new TLS state and warms a
    connection cache. Reusing sessions across requests is significantly
    cheaper than creating one per call. The HttpClient previously rotated
    sessions only on errors; this pool generalizes that pattern.

Design:
    - Bounded pool with `size` slots.
    - Each slot tracks: total_uses, errors, created_at.
    - On acquire(): caller borrows a session.
    - On release(): caller returns it. If marked unhealthy, the session is
      closed and a fresh one is queued.
    - max_uses_per_session: after N uses, the session is recycled
      (mitigates connection-cache poisoning by Instagram CDN).
    - max_age_seconds: after N seconds, recycle regardless of use count.

Usage:
    pool = ConnectionPool(PoolConfig(size=5, impersonate="chrome142"))

    with pool.acquire() as session:
        response = session.get("https://www.instagram.com/...")

    # Manual:
    handle = pool.acquire()
    try:
        ...
    finally:
        pool.release(handle, healthy=True)
"""

import asyncio
import logging
import queue
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

logger = logging.getLogger("instaharvest_v2.core.connection_pool")


@dataclass(frozen=True)
class PoolConfig:
    """
    Configuration for a connection pool.

    Args:
        size: Number of session slots.
        impersonate: curl_cffi impersonation profile (e.g., "chrome142").
        max_uses_per_session: Recycle after this many requests (0 = no limit).
        max_age_seconds: Recycle after this many seconds (0 = no limit).
        max_consecutive_errors: Mark session unhealthy after N errors.
        acquire_timeout: Max time to wait for a free session (seconds).
    """

    size: int = 5
    impersonate: str = "chrome142"
    max_uses_per_session: int = 500
    max_age_seconds: float = 1800.0
    max_consecutive_errors: int = 3
    acquire_timeout: Optional[float] = 30.0

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("PoolConfig.size must be >= 1")


@dataclass
class _SessionHandle:
    """Internal wrapper tracking a single pooled session."""

    session: Any                       # curl_cffi.Session or AsyncSession
    created_at: float
    total_uses: int = 0
    consecutive_errors: int = 0
    last_used_at: float = field(default_factory=time.time)


class ConnectionPool:
    """
    Thread-safe sync session pool.

    Sessions are lazily created on first acquire(). Closed pool releases
    every underlying session.
    """

    def __init__(
        self,
        config: Optional[PoolConfig] = None,
        session_factory: Optional[Callable[[str], Any]] = None,
    ):
        self._config = config or PoolConfig()
        self._factory = session_factory or self._default_factory
        self._available: "queue.LifoQueue[_SessionHandle]" = queue.LifoQueue(
            maxsize=self._config.size,
        )
        self._lock = threading.Lock()
        self._created_count: int = 0
        self._closed: bool = False
        self._stats = {
            "acquires": 0,
            "creates": 0,
            "recycles": 0,
            "errors": 0,
        }

    # ─── Public API ────────────────────────────────────────

    @contextmanager
    def acquire(self) -> Iterator[Any]:
        """Context manager. Yields a curl_cffi session."""
        if self._closed:
            raise RuntimeError("ConnectionPool is closed")

        handle = self._acquire_handle()
        healthy = True
        try:
            yield handle.session
        except Exception:
            healthy = False
            raise
        finally:
            self._release_handle(handle, healthy=healthy)

    def acquire_handle(self) -> _SessionHandle:
        """
        Lower-level: acquire a handle. Caller MUST call release_handle().
        """
        if self._closed:
            raise RuntimeError("ConnectionPool is closed")
        return self._acquire_handle()

    def release_handle(self, handle: _SessionHandle, healthy: bool = True) -> None:
        """Return a handle to the pool. Closes it if unhealthy or recyclable."""
        self._release_handle(handle, healthy=healthy)

    def close(self) -> None:
        """Close every underlying session and stop accepting acquires."""
        with self._lock:
            if self._closed:
                return
            self._closed = True

        # Drain queue and close everything
        while True:
            try:
                handle = self._available.get_nowait()
            except queue.Empty:
                break
            self._safe_close(handle.session)

    def __enter__(self) -> "ConnectionPool":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                **self._stats,
                "created_count": self._created_count,
                "available": self._available.qsize(),
                "size": self._config.size,
                "closed": self._closed,
            }

    # ─── Internal ──────────────────────────────────────────

    def _acquire_handle(self) -> _SessionHandle:
        with self._lock:
            self._stats["acquires"] += 1
            # If we haven't reached pool size, create a new session immediately
            if (
                self._available.qsize() == 0
                and self._created_count < self._config.size
            ):
                handle = self._create_handle()
                return handle

        try:
            handle = self._available.get(timeout=self._config.acquire_timeout)
        except queue.Empty:
            raise TimeoutError(
                f"ConnectionPool.acquire timeout after "
                f"{self._config.acquire_timeout}s"
            )

        # Recycle stale handles before handing them out
        if self._should_recycle(handle):
            self._safe_close(handle.session)
            with self._lock:
                self._created_count = max(0, self._created_count - 1)
                self._stats["recycles"] += 1
                handle = self._create_handle()

        return handle

    def _release_handle(self, handle: _SessionHandle, healthy: bool) -> None:
        if self._closed:
            self._safe_close(handle.session)
            return

        handle.total_uses += 1
        handle.last_used_at = time.time()
        if healthy:
            handle.consecutive_errors = 0
        else:
            handle.consecutive_errors += 1
            with self._lock:
                self._stats["errors"] += 1

        # Recycle if unhealthy or aged out
        if (
            handle.consecutive_errors >= self._config.max_consecutive_errors
            or self._should_recycle(handle)
        ):
            self._safe_close(handle.session)
            with self._lock:
                self._created_count = max(0, self._created_count - 1)
                self._stats["recycles"] += 1
            return

        try:
            self._available.put_nowait(handle)
        except queue.Full:
            # Pool oversubscribed (shouldn't happen) — close the extra
            self._safe_close(handle.session)
            with self._lock:
                self._created_count = max(0, self._created_count - 1)

    def _create_handle(self) -> _SessionHandle:
        """Create new session. Caller must hold the lock."""
        session = self._factory(self._config.impersonate)
        self._created_count += 1
        self._stats["creates"] += 1
        return _SessionHandle(session=session, created_at=time.time())

    def _should_recycle(self, handle: _SessionHandle) -> bool:
        cfg = self._config
        if cfg.max_uses_per_session > 0 and handle.total_uses >= cfg.max_uses_per_session:
            return True
        if cfg.max_age_seconds > 0 and (time.time() - handle.created_at) >= cfg.max_age_seconds:
            return True
        return False

    @staticmethod
    def _default_factory(impersonate: str) -> Any:
        """Default factory: curl_cffi.Session with the given impersonation."""
        from curl_cffi import requests as curl_requests
        return curl_requests.Session(impersonate=impersonate)

    @staticmethod
    def _safe_close(session: Any) -> None:
        try:
            session.close()
        except Exception as exc:
            logger.debug("Session close failed: %s", exc)


class AsyncConnectionPool:
    """
    Async equivalent of ConnectionPool.

    Uses asyncio.Queue. Each acquire() yields an AsyncSession via async
    context manager.
    """

    def __init__(
        self,
        config: Optional[PoolConfig] = None,
        session_factory: Optional[Callable[[str], Any]] = None,
    ):
        self._config = config or PoolConfig()
        self._factory = session_factory or self._default_factory
        self._available: Optional[asyncio.LifoQueue] = None
        self._init_lock = threading.Lock()
        self._created_count: int = 0
        self._closed: bool = False
        self._stats = {
            "acquires": 0,
            "creates": 0,
            "recycles": 0,
            "errors": 0,
        }

    def _ensure_queue(self) -> asyncio.LifoQueue:
        if self._available is None:
            with self._init_lock:
                if self._available is None:
                    self._available = asyncio.LifoQueue(maxsize=self._config.size)
        return self._available

    @contextmanager
    def _track_release(self, handle: _SessionHandle, healthy_ref: list) -> Iterator[None]:
        try:
            yield
        finally:
            pass  # async release done by caller

    async def acquire(self) -> "_AsyncAcquireContext":
        """Async context manager. Use `async with pool.acquire() as session:`."""
        if self._closed:
            raise RuntimeError("AsyncConnectionPool is closed")
        return _AsyncAcquireContext(self)

    async def acquire_handle(self) -> _SessionHandle:
        if self._closed:
            raise RuntimeError("AsyncConnectionPool is closed")
        return await self._acquire_handle_async()

    async def release_handle(
        self, handle: _SessionHandle, healthy: bool = True,
    ) -> None:
        await self._release_handle_async(handle, healthy=healthy)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._available is None:
            return
        while not self._available.empty():
            try:
                handle = self._available.get_nowait()
            except asyncio.QueueEmpty:
                break
            await self._safe_close(handle.session)

    @property
    def stats(self) -> dict:
        return {
            **self._stats,
            "created_count": self._created_count,
            "available": self._available.qsize() if self._available else 0,
            "size": self._config.size,
            "closed": self._closed,
        }

    # ─── Internal ──────────────────────────────────────────

    async def _acquire_handle_async(self) -> _SessionHandle:
        queue_ = self._ensure_queue()
        self._stats["acquires"] += 1

        if (
            queue_.qsize() == 0
            and self._created_count < self._config.size
        ):
            return await self._create_handle_async()

        try:
            handle = await asyncio.wait_for(
                queue_.get(),
                timeout=self._config.acquire_timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"AsyncConnectionPool.acquire timeout after "
                f"{self._config.acquire_timeout}s"
            )

        if self._should_recycle(handle):
            await self._safe_close(handle.session)
            self._created_count = max(0, self._created_count - 1)
            self._stats["recycles"] += 1
            handle = await self._create_handle_async()
        return handle

    async def _release_handle_async(
        self, handle: _SessionHandle, healthy: bool,
    ) -> None:
        if self._closed:
            await self._safe_close(handle.session)
            return

        handle.total_uses += 1
        handle.last_used_at = time.time()
        if healthy:
            handle.consecutive_errors = 0
        else:
            handle.consecutive_errors += 1
            self._stats["errors"] += 1

        if (
            handle.consecutive_errors >= self._config.max_consecutive_errors
            or self._should_recycle(handle)
        ):
            await self._safe_close(handle.session)
            self._created_count = max(0, self._created_count - 1)
            self._stats["recycles"] += 1
            return

        queue_ = self._ensure_queue()
        try:
            queue_.put_nowait(handle)
        except asyncio.QueueFull:
            await self._safe_close(handle.session)
            self._created_count = max(0, self._created_count - 1)

    async def _create_handle_async(self) -> _SessionHandle:
        session = self._factory(self._config.impersonate)
        self._created_count += 1
        self._stats["creates"] += 1
        return _SessionHandle(session=session, created_at=time.time())

    def _should_recycle(self, handle: _SessionHandle) -> bool:
        cfg = self._config
        if cfg.max_uses_per_session > 0 and handle.total_uses >= cfg.max_uses_per_session:
            return True
        if cfg.max_age_seconds > 0 and (time.time() - handle.created_at) >= cfg.max_age_seconds:
            return True
        return False

    @staticmethod
    def _default_factory(impersonate: str) -> Any:
        from curl_cffi.requests import AsyncSession
        return AsyncSession(impersonate=impersonate)

    @staticmethod
    async def _safe_close(session: Any) -> None:
        close = getattr(session, "close", None)
        if close is None:
            return
        try:
            result = close()
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            logger.debug("Async session close failed: %s", exc)


class _AsyncAcquireContext:
    """Async context manager returned by AsyncConnectionPool.acquire()."""

    __slots__ = ("_pool", "_handle", "_healthy")

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool
        self._handle: Optional[_SessionHandle] = None
        self._healthy = True

    async def __aenter__(self) -> Any:
        self._handle = await self._pool._acquire_handle_async()
        return self._handle.session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self._healthy = False
        if self._handle is not None:
            await self._pool._release_handle_async(self._handle, healthy=self._healthy)
            self._handle = None
