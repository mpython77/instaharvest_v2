"""
Circuit Breaker
================
Three-state failure isolation pattern preventing cascading failures.

States:
    CLOSED      — Normal operation. All requests pass through.
                  On consecutive failures >= threshold, transitions to OPEN.

    OPEN        — Fail-fast mode. All requests immediately raise CircuitOpenError.
                  After recovery_timeout, transitions to HALF_OPEN.

    HALF_OPEN   — Probe mode. A limited number of requests are allowed through.
                  On success: transitions to CLOSED.
                  On failure: transitions back to OPEN with full timeout.

Usage:
    breaker = CircuitBreaker(
        name="instagram_api",
        config=CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=3,
        ),
    )

    try:
        result = breaker.call(some_function, arg1, arg2)
    except CircuitOpenError:
        # Circuit is open — fail fast
        ...

    # Or as decorator:
    @breaker.protect
    def risky_call():
        ...

Per-endpoint isolation:
    registry = CircuitBreakerRegistry()
    breaker = registry.get_or_create("/api/users/", config=...)
    breaker.call(...)
"""

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, Optional, Type, Tuple

logger = logging.getLogger("instaharvest_v2.core.circuit_breaker")


class CircuitState(str, Enum):
    """Three states of the circuit breaker state machine."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """
    Raised when the circuit is OPEN and a call is attempted.
    Callers should treat this as fail-fast (do not retry).
    """

    def __init__(self, name: str, opened_at: float, recovery_at: float):
        self.name = name
        self.opened_at = opened_at
        self.recovery_at = recovery_at
        remaining = max(0, recovery_at - time.time())
        super().__init__(
            f"Circuit '{name}' is OPEN. "
            f"Recovery in {remaining:.1f}s."
        )


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for a single circuit breaker.

    Args:
        failure_threshold: Consecutive failures before opening the circuit.
        success_threshold: Successful HALF_OPEN calls needed to close the circuit.
        recovery_timeout: Seconds to wait in OPEN state before probing.
        half_open_max_calls: Max parallel calls allowed in HALF_OPEN state.
        excluded_exceptions: Exception types that should NOT count as failures
            (e.g., NotFoundError, PrivateAccountError — valid business outcomes).
        included_exceptions: If non-empty, ONLY these exception types count as
            failures. All others pass through without affecting state.
    """

    failure_threshold: int = 5
    success_threshold: int = 2
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    excluded_exceptions: Tuple[Type[BaseException], ...] = field(default_factory=tuple)
    included_exceptions: Tuple[Type[BaseException], ...] = field(default_factory=tuple)


class CircuitBreaker:
    """
    Thread-safe circuit breaker.

    Tracks consecutive failures and transitions through three states.
    All state transitions are atomic under an internal lock.
    """

    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._lock = threading.RLock()

        # State machine
        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._half_open_successes: int = 0
        self._half_open_in_flight: int = 0
        self._opened_at: float = 0.0
        self._last_failure_at: float = 0.0
        self._last_failure_msg: str = ""

        # Stats
        self._total_calls: int = 0
        self._total_failures: int = 0
        self._total_short_circuits: int = 0
        self._total_state_transitions: int = 0

    # ─── Public API ────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> CircuitState:
        """Current state. May trigger HALF_OPEN transition if recovery elapsed."""
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    @property
    def stats(self) -> Dict[str, Any]:
        """Snapshot of current statistics."""
        with self._lock:
            return {
                "name": self._name,
                "state": self._state.value,
                "consecutive_failures": self._consecutive_failures,
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_short_circuits": self._total_short_circuits,
                "total_state_transitions": self._total_state_transitions,
                "opened_at": self._opened_at,
                "last_failure_at": self._last_failure_at,
                "last_failure_msg": self._last_failure_msg,
                "failure_rate": (
                    self._total_failures / self._total_calls
                    if self._total_calls > 0 else 0.0
                ),
            }

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute func through the circuit breaker.

        Raises CircuitOpenError if the circuit is OPEN.
        Re-raises the original exception on failure.
        """
        self._before_call()
        try:
            result = func(*args, **kwargs)
        except BaseException as exc:
            self._on_failure(exc)
            raise
        else:
            self._on_success()
            return result

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Async equivalent of `call()`. `func` must be a coroutine function."""
        self._before_call()
        try:
            result = await func(*args, **kwargs)
        except BaseException as exc:
            self._on_failure(exc)
            raise
        else:
            self._on_success()
            return result

    def protect(self, func: Callable) -> Callable:
        """Decorator form. Wraps a callable with `call()`."""
        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(func, *args, **kwargs)

        return wrapper

    @contextmanager
    def attempt(self) -> Iterator["CircuitBreaker"]:
        """
        Context manager equivalent of `call()`.

        Use when you need to interleave breaker state transitions with
        existing retry / rotation / response-handling logic.

        Example:
            for retry in range(max_retries):
                try:
                    with breaker.attempt():
                        response = make_http_call()
                        validate(response)
                except CircuitOpenError:
                    raise  # do not retry — breaker is open
                except TransientError:
                    continue  # retry; breaker has already counted the failure
        """
        self._before_call()
        try:
            yield self
        except BaseException as exc:
            self._on_failure(exc)
            raise
        else:
            self._on_success()

    def reset(self) -> None:
        """Force the circuit back to CLOSED state and clear counters."""
        with self._lock:
            self._transition(CircuitState.CLOSED, reason="manual_reset")
            self._consecutive_failures = 0
            self._half_open_successes = 0
            self._half_open_in_flight = 0

    def force_open(self) -> None:
        """Force the circuit to OPEN state (e.g., during maintenance)."""
        with self._lock:
            self._transition(CircuitState.OPEN, reason="manual_open")
            self._opened_at = time.time()

    # ─── Internal state machine ────────────────────────────

    def _before_call(self) -> None:
        """Check state and either allow the call or short-circuit."""
        with self._lock:
            self._total_calls += 1
            self._maybe_transition_to_half_open()

            if self._state is CircuitState.OPEN:
                self._total_short_circuits += 1
                raise CircuitOpenError(
                    name=self._name,
                    opened_at=self._opened_at,
                    recovery_at=self._opened_at + self._config.recovery_timeout,
                )

            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_in_flight >= self._config.half_open_max_calls:
                    self._total_short_circuits += 1
                    raise CircuitOpenError(
                        name=self._name,
                        opened_at=self._opened_at,
                        recovery_at=self._opened_at + self._config.recovery_timeout,
                    )
                self._half_open_in_flight += 1

    def _on_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._half_open_in_flight = max(0, self._half_open_in_flight - 1)
                self._half_open_successes += 1
                if self._half_open_successes >= self._config.success_threshold:
                    self._transition(CircuitState.CLOSED, reason="recovery_confirmed")
                    self._consecutive_failures = 0
                    self._half_open_successes = 0
            else:
                # CLOSED: reset failure streak on every success
                self._consecutive_failures = 0

    def _on_failure(self, exc: BaseException) -> None:
        if not self._is_counted_failure(exc):
            # Decrement in-flight if this was a HALF_OPEN probe
            with self._lock:
                if self._state is CircuitState.HALF_OPEN:
                    self._half_open_in_flight = max(0, self._half_open_in_flight - 1)
            return

        with self._lock:
            self._total_failures += 1
            self._consecutive_failures += 1
            self._last_failure_at = time.time()
            self._last_failure_msg = f"{type(exc).__name__}: {exc}"[:200]

            if self._state is CircuitState.HALF_OPEN:
                # A single failure in HALF_OPEN reopens the circuit
                self._half_open_in_flight = max(0, self._half_open_in_flight - 1)
                self._transition(CircuitState.OPEN, reason="probe_failed")
                self._opened_at = time.time()
                self._half_open_successes = 0

            elif self._state is CircuitState.CLOSED:
                if self._consecutive_failures >= self._config.failure_threshold:
                    self._transition(CircuitState.OPEN, reason="threshold_exceeded")
                    self._opened_at = time.time()

    def _is_counted_failure(self, exc: BaseException) -> bool:
        """
        Check whether `exc` should be counted as a failure for this breaker.
        Excluded exceptions (valid business outcomes) are ignored.
        """
        excluded = self._config.excluded_exceptions
        if excluded and isinstance(exc, excluded):
            return False

        included = self._config.included_exceptions
        if included:
            return isinstance(exc, included)

        return True

    def _maybe_transition_to_half_open(self) -> None:
        """If OPEN and recovery_timeout has elapsed, move to HALF_OPEN."""
        if self._state is not CircuitState.OPEN:
            return
        elapsed = time.time() - self._opened_at
        if elapsed >= self._config.recovery_timeout:
            self._transition(CircuitState.HALF_OPEN, reason="recovery_window_started")
            self._half_open_in_flight = 0
            self._half_open_successes = 0

    def _transition(self, new_state: CircuitState, reason: str) -> None:
        if self._state is new_state:
            return
        old = self._state
        self._state = new_state
        self._total_state_transitions += 1
        logger.info(
            "Circuit '%s' transition: %s -> %s (reason=%s)",
            self._name, old.value, new_state.value, reason,
        )

    def __repr__(self) -> str:
        return (
            f"<CircuitBreaker name={self._name!r} state={self._state.value} "
            f"failures={self._consecutive_failures}/{self._config.failure_threshold}>"
        )


class CircuitBreakerRegistry:
    """
    Registry for per-endpoint circuit breakers.

    Each unique key (e.g., URL pattern, endpoint name) gets its own
    independent CircuitBreaker, so a failing endpoint does not impact
    healthy ones.

    Usage:
        registry = CircuitBreakerRegistry(default_config=CircuitBreakerConfig())
        breaker = registry.get_or_create("/api/v1/users/")
        breaker.call(http_call)
    """

    def __init__(
        self,
        default_config: Optional[CircuitBreakerConfig] = None,
    ):
        self._default_config = default_config or CircuitBreakerConfig()
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        key: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Return an existing breaker for `key` or create a new one."""
        with self._lock:
            breaker = self._breakers.get(key)
            if breaker is None:
                breaker = CircuitBreaker(name=key, config=config or self._default_config)
                self._breakers[key] = breaker
            return breaker

    def get(self, key: str) -> Optional[CircuitBreaker]:
        """Return an existing breaker for `key`, or None."""
        return self._breakers.get(key)

    def reset_all(self) -> None:
        """Reset every registered breaker to CLOSED state."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def stats(self) -> Dict[str, Dict[str, Any]]:
        """Return statistics for every registered breaker."""
        with self._lock:
            return {key: breaker.stats for key, breaker in self._breakers.items()}

    def __len__(self) -> int:
        return len(self._breakers)

    def __contains__(self, key: str) -> bool:
        return key in self._breakers
