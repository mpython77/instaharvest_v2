"""
Structured Logger
=================
JSON-formatted log entries with correlation IDs and automatic PII
redaction.

Why structured:
    The existing emoji-based logging is great for humans but impossible to
    parse for log aggregators (CloudWatch, Datadog, Loki, ELK). This logger
    emits one JSON object per line so every field is queryable.

Correlation IDs:
    Every request gets a `correlation_id` (short UUID). All log entries
    emitted while processing that request carry the same ID, so you can
    `grep` for a single request across the whole pipeline.

PII redaction:
    Session IDs, CSRF tokens, cookies, Authorization headers, and email
    addresses are automatically redacted before serialization. The redactor
    is configurable.

Usage:
    log = StructuredLogger("instaharvest_v2.http")

    with log.context(correlation_id="abc123", endpoint="/users"):
        log.info("request_start", method="GET", url="...")
        log.error(
            "request_failed",
            status_code=500,
            error="ServerError",
        )

    # Plain logging without a context:
    log.info("startup_complete", version="1.1.88")

Output (one line per record):
    {"ts":"2026-05-28T10:00:00Z","level":"INFO","logger":"instaharvest_v2.http",
     "event":"request_start","correlation_id":"abc123","method":"GET","url":"..."}
"""

import contextvars
import io
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Pattern, TextIO


# ─── Correlation ID context ────────────────────────────────


_correlation_id: "contextvars.ContextVar[Optional[str]]" = contextvars.ContextVar(
    "correlation_id", default=None,
)


def correlation_id() -> str:
    """
    Return the current correlation ID, generating one if not set.
    Lookup is per-task (asyncio) or per-thread.
    """
    cid = _correlation_id.get()
    if cid is None:
        cid = uuid.uuid4().hex[:12]
        _correlation_id.set(cid)
    return cid


def set_correlation_id(value: Optional[str]) -> "contextvars.Token":
    """Override the correlation ID. Returns a token for restoration."""
    return _correlation_id.set(value)


def reset_correlation_id(token: "contextvars.Token") -> None:
    """Restore the correlation ID to the value before `set_correlation_id`."""
    _correlation_id.reset(token)


# ─── PII redaction ─────────────────────────────────────────


# Default keys whose values should be fully masked.
DEFAULT_REDACT_KEYS: frozenset = frozenset({
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth", "cookie", "cookies", "set-cookie",
    "session_id", "sessionid", "csrf_token", "csrftoken",
    "x-csrftoken", "x-ig-www-claim", "ig_www_claim",
    "fb_dtsg", "lsd", "private_key", "encryption_key",
})

# Inline patterns to redact regardless of key.
_EMAIL_RE: Pattern[str] = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
)
_LONG_HEX_RE: Pattern[str] = re.compile(
    r"\b[A-Fa-f0-9]{20,}\b",
)


def _redact_value(value: Any) -> str:
    """
    Replace the body of a sensitive value with `***` while preserving
    a hint about its length and a small prefix for debugging.
    """
    if value is None:
        return "None"
    s = str(value)
    if len(s) <= 4:
        return "***"
    return f"{s[:2]}***({len(s)} chars)"


def _redact_payload(
    payload: Any,
    redact_keys: frozenset,
) -> Any:
    """
    Recursively walk dict/list/tuple structures, masking values whose
    key matches `redact_keys`. Strings have inline patterns redacted.
    """
    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            key_norm = str(k).lower()
            if key_norm in redact_keys:
                out[k] = _redact_value(v)
            else:
                out[k] = _redact_payload(v, redact_keys)
        return out
    if isinstance(payload, (list, tuple)):
        return [_redact_payload(item, redact_keys) for item in payload]
    if isinstance(payload, str):
        return _redact_string(payload)
    return payload


def _redact_string(s: str) -> str:
    """Mask emails and long hex tokens inside free-form strings."""
    s = _EMAIL_RE.sub(
        lambda m: m.group(0)[0] + "***@***" + m.group(0).rsplit(".", 1)[-1],
        s,
    )
    s = _LONG_HEX_RE.sub(
        lambda m: m.group(0)[:4] + "***",
        s,
    )
    return s


# ─── Context object ────────────────────────────────────────


@dataclass
class LogContext:
    """
    Mutable context attached to a logger. Fields here are merged into
    every record emitted while the context is active.
    """

    fields: Dict[str, Any] = field(default_factory=dict)


# ─── The logger ────────────────────────────────────────────


# Map from `level` name string to int.
_LEVELS: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class StructuredLogger:
    """
    Emits one JSON line per record.

    Args:
        name: Logger name (typically the module path).
        level: Minimum level to emit. Default INFO.
        stream: Output stream. Default sys.stderr.
        redact_keys: Set of (lowercased) field names whose values
            should be masked. Default: DEFAULT_REDACT_KEYS.
        extra_fields: Static fields included on every record
            (e.g., {"service": "instaharvest_v2", "env": "prod"}).
        sort_keys: Sort JSON keys for deterministic output (default True).
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        stream: Optional[TextIO] = None,
        redact_keys: Optional[frozenset] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
        sort_keys: bool = True,
    ):
        self._name = name
        self._level = level
        self._stream = stream if stream is not None else sys.stderr
        self._redact_keys = redact_keys or DEFAULT_REDACT_KEYS
        self._extra_fields = dict(extra_fields or {})
        self._sort_keys = sort_keys
        self._lock = threading.Lock()
        self._stack: List[Dict[str, Any]] = []
        self._stack_lock = threading.Lock()

    # ─── Configuration ─────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> int:
        return self._level

    def set_level(self, level: int) -> None:
        self._level = level

    def add_extra(self, **fields: Any) -> None:
        """Add static fields to every record (merged on top)."""
        self._extra_fields.update(fields)

    # ─── Context management ────────────────────────────────

    @contextmanager
    def context(self, **fields: Any) -> Iterator[None]:
        """
        Push fields onto the per-logger stack for the duration of the block.
        Nested contexts merge — inner fields override outer ones.

        If `correlation_id` is not in fields, one is generated automatically
        for the duration of the block.
        """
        cid_token: Optional[contextvars.Token] = None
        if "correlation_id" not in fields:
            cid_token = set_correlation_id(uuid.uuid4().hex[:12])
        else:
            cid_token = set_correlation_id(str(fields.pop("correlation_id")))

        with self._stack_lock:
            self._stack.append(dict(fields))
        try:
            yield
        finally:
            with self._stack_lock:
                self._stack.pop()
            if cid_token is not None:
                reset_correlation_id(cid_token)

    # ─── Emission API ──────────────────────────────────────

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, "DEBUG", event, fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, "INFO", event, fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, "WARNING", event, fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, "ERROR", event, fields)

    def critical(self, event: str, **fields: Any) -> None:
        self._emit(logging.CRITICAL, "CRITICAL", event, fields)

    def log(
        self,
        level: int,
        event: str,
        **fields: Any,
    ) -> None:
        level_name = logging.getLevelName(level) if isinstance(level, int) else str(level)
        self._emit(level, level_name, event, fields)

    # ─── Internal ──────────────────────────────────────────

    def _emit(
        self,
        level: int,
        level_name: str,
        event: str,
        fields: Dict[str, Any],
    ) -> None:
        if level < self._level:
            return

        record: Dict[str, Any] = {
            "ts": _now_iso(),
            "level": level_name,
            "logger": self._name,
            "event": event,
            "correlation_id": _correlation_id.get() or "-",
        }

        # Static extras (lowest priority)
        record.update(self._extra_fields)

        # Stacked context (mid priority)
        with self._stack_lock:
            for frame in self._stack:
                record.update(frame)

        # Per-call fields (highest priority)
        record.update(fields)

        # Redact sensitive fields
        record = _redact_payload(record, self._redact_keys)

        try:
            line = json.dumps(record, sort_keys=self._sort_keys, default=_json_default)
        except (TypeError, ValueError):
            # Last-ditch: stringify everything
            safe = {k: repr(v) for k, v in record.items()}
            line = json.dumps(safe, sort_keys=self._sort_keys)

        with self._lock:
            self._stream.write(line)
            self._stream.write("\n")
            try:
                self._stream.flush()
            except Exception:
                pass


# ─── Helpers ───────────────────────────────────────────────


def _now_iso() -> str:
    """ISO-8601 UTC timestamp with millisecond resolution."""
    t = time.time()
    secs = int(t)
    msec = int((t - secs) * 1000)
    tm = time.gmtime(secs)
    return (
        f"{tm.tm_year:04d}-{tm.tm_mon:02d}-{tm.tm_mday:02d}"
        f"T{tm.tm_hour:02d}:{tm.tm_min:02d}:{tm.tm_sec:02d}"
        f".{msec:03d}Z"
    )


def _json_default(obj: Any) -> Any:
    """Fallback serializer for json.dumps."""
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8", errors="replace")
        except Exception:
            return repr(obj)
    return repr(obj)
