"""
Metrics Collector
=================
Prometheus-compatible in-process metrics: Counter, Gauge, Histogram.

Why in-process:
    Most users will never spin up a Prometheus scraper. The metrics are
    valuable for ad-hoc inspection (`metrics.snapshot()`), debugging, and
    optional export. We avoid adding `prometheus_client` as a dependency.

Metric types:
    Counter  : monotonically increasing (e.g., total_requests).
    Gauge    : arbitrary up/down value (e.g., open_circuits).
    Histogram: distribution with configurable buckets (e.g., request_duration).

All types support labels (a tuple of key=value pairs). Each unique label
combination is its own series.

Usage:
    from instaharvest_v2.core import metrics

    metrics.counter("requests_total").inc()
    metrics.counter("requests_total", labels={"method": "GET"}).inc()
    metrics.gauge("active_sessions").set(5)
    metrics.histogram("request_duration_seconds").observe(0.42)

    # Export
    print(metrics.snapshot())                # dict
    print(metrics.export_prometheus())       # text format
"""

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger("instaharvest_v2.core.metrics")


# Label sets are stored as frozensets of (key, value) tuples for hashability.
LabelKey = FrozenSet[Tuple[str, str]]


def _label_key(labels: Optional[Dict[str, str]]) -> LabelKey:
    """Convert a {k: v} dict into a hashable, order-independent key."""
    if not labels:
        return frozenset()
    return frozenset((str(k), str(v)) for k, v in labels.items())


def _format_labels(labels: LabelKey) -> str:
    """Render labels as `{k1="v1",k2="v2"}` Prometheus syntax."""
    if not labels:
        return ""
    parts = sorted(labels)
    rendered = ",".join(f'{k}="{_escape(v)}"' for k, v in parts)
    return "{" + rendered + "}"


def _escape(value: str) -> str:
    """Escape `"` and `\\` and newlines for Prometheus label values."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# ─── Metric primitives ──────────────────────────────────────


class _SeriesBase:
    """Common state for a per-label series."""

    __slots__ = ("labels", "value", "updated_at")

    def __init__(self, labels: LabelKey):
        self.labels: LabelKey = labels
        self.value: float = 0.0
        self.updated_at: float = time.time()


class Counter:
    """
    Monotonically increasing counter.

    Use for cumulative totals (requests, errors, bytes).
    """

    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._series: Dict[LabelKey, _SeriesBase] = {}
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    def inc(
        self,
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        if amount < 0:
            raise ValueError("Counter cannot be decremented")
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                series = _SeriesBase(key)
                self._series[key] = series
            series.value += amount
            series.updated_at = time.time()

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            return series.value if series else 0.0

    def reset(self) -> None:
        with self._lock:
            self._series.clear()

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "labels": dict(s.labels),
                    "value": s.value,
                    "updated_at": s.updated_at,
                }
                for s in self._series.values()
            ]

    def export_prometheus(self) -> str:
        lines: List[str] = []
        if self._description:
            lines.append(f"# HELP {self._name} {self._description}")
        lines.append(f"# TYPE {self._name} counter")
        with self._lock:
            for series in self._series.values():
                lines.append(
                    f"{self._name}{_format_labels(series.labels)} {series.value}"
                )
        return "\n".join(lines)


class Gauge:
    """
    Arbitrary up/down value.

    Use for instantaneous measurements (queue size, active connections,
    open circuits).
    """

    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._series: Dict[LabelKey, _SeriesBase] = {}
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                series = _SeriesBase(key)
                self._series[key] = series
            series.value = float(value)
            series.updated_at = time.time()

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                series = _SeriesBase(key)
                self._series[key] = series
            series.value += amount
            series.updated_at = time.time()

    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        self.inc(amount=-amount, labels=labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            return series.value if series else 0.0

    def reset(self) -> None:
        with self._lock:
            self._series.clear()

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "labels": dict(s.labels),
                    "value": s.value,
                    "updated_at": s.updated_at,
                }
                for s in self._series.values()
            ]

    def export_prometheus(self) -> str:
        lines: List[str] = []
        if self._description:
            lines.append(f"# HELP {self._name} {self._description}")
        lines.append(f"# TYPE {self._name} gauge")
        with self._lock:
            for series in self._series.values():
                lines.append(
                    f"{self._name}{_format_labels(series.labels)} {series.value}"
                )
        return "\n".join(lines)


# Default histogram buckets in seconds, suited for HTTP request durations.
DEFAULT_HISTOGRAM_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
)


@dataclass
class _HistogramSeries:
    """Per-label histogram state."""

    labels: LabelKey
    bucket_counts: List[int] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0
    updated_at: float = field(default_factory=time.time)


class Histogram:
    """
    Distribution metric with cumulative buckets.

    Buckets are upper-bound inclusive: an observation of 0.42 increments
    every bucket whose upper-bound is >= 0.42, plus the +Inf bucket.

    Use for latencies, sizes, anything you'd want a P50/P99 of.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[Tuple[float, ...]] = None,
    ):
        self._name = name
        self._description = description
        # Always append +Inf bucket implicitly via len(buckets) + 1
        self._buckets: Tuple[float, ...] = tuple(
            sorted(buckets if buckets is not None else DEFAULT_HISTOGRAM_BUCKETS)
        )
        self._series: Dict[LabelKey, _HistogramSeries] = {}
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def buckets(self) -> Tuple[float, ...]:
        return self._buckets

    def observe(
        self,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                series = _HistogramSeries(
                    labels=key,
                    bucket_counts=[0] * (len(self._buckets) + 1),
                )
                self._series[key] = series

            # Increment every bucket >= value
            for i, upper in enumerate(self._buckets):
                if value <= upper:
                    series.bucket_counts[i] += 1
            # +Inf bucket always increments
            series.bucket_counts[-1] += 1

            series.sum += value
            series.count += 1
            series.updated_at = time.time()

    def time(self, labels: Optional[Dict[str, str]] = None) -> "_HistogramTimer":
        """Context manager that observes the elapsed seconds."""
        return _HistogramTimer(self, labels)

    def get(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Snapshot of one series."""
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None:
                return {"count": 0, "sum": 0.0, "buckets": {}}
            return self._series_to_dict(series)

    def quantile(
        self,
        q: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """
        Approximate q-th quantile (0.0 <= q <= 1.0) using bucket counts.

        Returns None if no observations recorded.
        """
        if not 0.0 <= q <= 1.0:
            raise ValueError("quantile q must be in [0, 1]")
        key = _label_key(labels)
        with self._lock:
            series = self._series.get(key)
            if series is None or series.count == 0:
                return None
            target = q * series.count
            cumulative = 0
            for i, upper in enumerate(self._buckets):
                cumulative = series.bucket_counts[i]
                if cumulative >= target:
                    return upper
            # Falls into +Inf bucket
            return math.inf

    def reset(self) -> None:
        with self._lock:
            self._series.clear()

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._series_to_dict(s) for s in self._series.values()]

    def export_prometheus(self) -> str:
        lines: List[str] = []
        if self._description:
            lines.append(f"# HELP {self._name} {self._description}")
        lines.append(f"# TYPE {self._name} histogram")

        with self._lock:
            for series in self._series.values():
                base_labels = dict(series.labels)
                cumulative = 0
                for i, upper in enumerate(self._buckets):
                    cumulative = series.bucket_counts[i]
                    bl = dict(base_labels, le=str(upper))
                    lines.append(
                        f"{self._name}_bucket{_format_labels(_label_key(bl))} {cumulative}"
                    )
                # +Inf
                bl = dict(base_labels, le="+Inf")
                lines.append(
                    f"{self._name}_bucket{_format_labels(_label_key(bl))} "
                    f"{series.bucket_counts[-1]}"
                )
                lines.append(
                    f"{self._name}_sum{_format_labels(series.labels)} {series.sum}"
                )
                lines.append(
                    f"{self._name}_count{_format_labels(series.labels)} {series.count}"
                )

        return "\n".join(lines)

    def _series_to_dict(self, series: _HistogramSeries) -> Dict[str, Any]:
        bucket_view: Dict[str, int] = {}
        for i, upper in enumerate(self._buckets):
            bucket_view[str(upper)] = series.bucket_counts[i]
        bucket_view["+Inf"] = series.bucket_counts[-1]
        return {
            "labels": dict(series.labels),
            "count": series.count,
            "sum": series.sum,
            "buckets": bucket_view,
            "updated_at": series.updated_at,
        }


class _HistogramTimer:
    """Context manager that observes elapsed seconds in a Histogram."""

    __slots__ = ("_hist", "_labels", "_start")

    def __init__(self, histogram: Histogram, labels: Optional[Dict[str, str]]):
        self._hist = histogram
        self._labels = labels
        self._start: float = 0.0

    def __enter__(self) -> "_HistogramTimer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed = time.monotonic() - self._start
        self._hist.observe(elapsed, labels=self._labels)


# ─── Registry ──────────────────────────────────────────────


class MetricsRegistry:
    """
    Central registry for metrics. Behaves like a singleton — `metrics`
    module-level instance is what most callers use.

    The registry hands out Counter/Gauge/Histogram instances on demand
    and never duplicates names.
    """

    def __init__(self) -> None:
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, description: str = "") -> Counter:
        with self._lock:
            existing = self._counters.get(name)
            if existing is None:
                existing = Counter(name, description=description)
                self._counters[name] = existing
            return existing

    def gauge(self, name: str, description: str = "") -> Gauge:
        with self._lock:
            existing = self._gauges.get(name)
            if existing is None:
                existing = Gauge(name, description=description)
                self._gauges[name] = existing
            return existing

    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[Tuple[float, ...]] = None,
    ) -> Histogram:
        with self._lock:
            existing = self._histograms.get(name)
            if existing is None:
                existing = Histogram(name, description=description, buckets=buckets)
                self._histograms[name] = existing
            return existing

    def reset(self) -> None:
        """Drop every series across every metric."""
        with self._lock:
            for c in self._counters.values():
                c.reset()
            for g in self._gauges.values():
                g.reset()
            for h in self._histograms.values():
                h.reset()

    def snapshot(self) -> Dict[str, Any]:
        """Return a structured snapshot of every metric."""
        with self._lock:
            return {
                "counters": {
                    name: c.snapshot() for name, c in self._counters.items()
                },
                "gauges": {
                    name: g.snapshot() for name, g in self._gauges.items()
                },
                "histograms": {
                    name: h.snapshot() for name, h in self._histograms.items()
                },
            }

    def export_prometheus(self) -> str:
        """Return a single text blob in Prometheus exposition format."""
        chunks: List[str] = []
        with self._lock:
            for c in self._counters.values():
                chunks.append(c.export_prometheus())
            for g in self._gauges.values():
                chunks.append(g.export_prometheus())
            for h in self._histograms.values():
                chunks.append(h.export_prometheus())
        return "\n".join(filter(None, chunks)) + "\n"


# Module-level default registry. Most callers should use this.
metrics = MetricsRegistry()
