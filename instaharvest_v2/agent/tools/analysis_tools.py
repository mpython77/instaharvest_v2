"""
Analysis Tools
==============
Data analysis and visualization handlers:
analyze_data, create_chart + helper functions.
"""

import csv
import json
import os
import statistics
import logging
from typing import Any, Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


def handle_analyze_data(args: Dict) -> str:
    """Analyze data from file or raw input."""
    source = args.get("source", "")
    analysis_type = args.get("analysis_type", "summary")
    field = args.get("field", None)
    top_n = args.get("top_n", 10)

    if not source:
        return "Error: no data source provided"

    # Load data
    data = _load_data(source)
    if isinstance(data, str):
        return data  # Error message

    if not data:
        return "Error: no data to analyze"

    try:
        if analysis_type == "summary":
            return _analyze_summary(data, field)
        elif analysis_type == "top_n":
            return _analyze_top_n(data, field, top_n)
        elif analysis_type == "distribution":
            return _analyze_distribution(data, field)
        elif analysis_type == "compare":
            return _analyze_compare(data, field)
        elif analysis_type == "trend":
            return _analyze_trend(data, field)
        else:
            return f"Error: unknown analysis type '{analysis_type}'. Use: summary, top_n, distribution, compare, trend"

    except Exception as e:
        return f"Error analyzing data: {e}"


def _load_data(source: str) -> Any:
    """Load data from file path or raw JSON string."""
    # Try as file first
    if os.path.exists(source):
        ext = os.path.splitext(source)[1].lower()
        try:
            if ext == ".json":
                with open(source, "r", encoding="utf-8") as f:
                    return json.load(f)
            elif ext == ".jsonl":
                with open(source, "r", encoding="utf-8") as f:
                    return [json.loads(line) for line in f if line.strip()]
            elif ext in (".csv", ".tsv"):
                delimiter = "\t" if ext == ".tsv" else ","
                with open(source, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    return list(reader)
            else:
                with open(source, "r", encoding="utf-8") as f:
                    return [{"line": line.strip()} for line in f if line.strip()]
        except Exception as e:
            return f"Error loading '{source}': {e}"

    # Try as raw JSON
    try:
        return json.loads(source)
    except (json.JSONDecodeError, TypeError):
        return f"Error: '{source}' is not a valid file path or JSON data"


def _analyze_summary(data, field=None):
    """Generate summary statistics."""
    if isinstance(data, list) and data:
        lines = [f"📊 Data Summary ({len(data)} records)"]
        lines.append("-" * 40)

        if isinstance(data[0], dict):
            keys = list(data[0].keys())
            lines.append(f"Fields: {', '.join(keys[:15])}")

            # Numeric fields stats
            for key in keys[:10]:
                values = [_to_num(item.get(key)) for item in data if _to_num(item.get(key)) is not None]
                if values and len(values) >= 2:
                    lines.append(f"\n  {key}:")
                    lines.append(f"    Count: {len(values)}")
                    lines.append(f"    Min: {min(values):,.2f}")
                    lines.append(f"    Max: {max(values):,.2f}")
                    lines.append(f"    Avg: {statistics.mean(values):,.2f}")
                    lines.append(f"    Median: {statistics.median(values):,.2f}")

        return "\n".join(lines)

    return f"Data: {type(data).__name__} with {len(data) if hasattr(data, '__len__') else '?'} items"


def _analyze_top_n(data, field, n=10):
    """Get top N items by a field."""
    if not field or not isinstance(data, list):
        return "Error: 'field' required for top_n analysis"

    try:
        sorted_data = sorted(
            [d for d in data if _to_num(d.get(field)) is not None],
            key=lambda x: _to_num(x.get(field, 0)),
            reverse=True
        )

        lines = [f"🏆 Top {n} by '{field}':"]
        lines.append("-" * 40)

        for i, item in enumerate(sorted_data[:n], 1):
            name = item.get("username") or item.get("name") or item.get("id") or f"#{i}"
            value = item.get(field)
            lines.append(f"  {i}. {name}: {value:,}" if isinstance(value, (int, float)) else f"  {i}. {name}: {value}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error in top_n analysis: {e}"


def _analyze_distribution(data, field):
    """Analyze value distribution."""
    if not field or not isinstance(data, list):
        return "Error: 'field' required for distribution analysis"

    values = [item.get(field) for item in data if item.get(field) is not None]
    if not values:
        return f"Error: no values found for field '{field}'"

    numeric = [_to_num(v) for v in values if _to_num(v) is not None]

    if numeric:
        lines = [f"📈 Distribution of '{field}' ({len(numeric)} values):"]
        lines.append("-" * 40)

        # Ranges
        min_v, max_v = min(numeric), max(numeric)
        range_size = (max_v - min_v) / 5 if max_v != min_v else 1
        buckets = {}
        for v in numeric:
            bucket = int((v - min_v) / range_size) if range_size else 0
            bucket = min(bucket, 4)
            low = min_v + bucket * range_size
            high = low + range_size
            key = f"{low:,.0f}-{high:,.0f}"
            buckets[key] = buckets.get(key, 0) + 1

        for key, count in sorted(buckets.items()):
            bar = "█" * min(count, 40)
            lines.append(f"  {key:>20s}: {bar} ({count})")

        return "\n".join(lines)

    # Categorical distribution
    from collections import Counter
    counter = Counter(values)
    lines = [f"📊 Distribution of '{field}' ({len(values)} values):"]
    for value, count in counter.most_common(20):
        bar = "█" * min(count, 30)
        lines.append(f"  {str(value):>20s}: {bar} ({count})")

    return "\n".join(lines)


def _analyze_compare(data, field):
    """Compare items."""
    if not isinstance(data, list) or len(data) < 2:
        return "Error: need at least 2 items to compare"

    lines = [f"⚖️ Comparison ({len(data)} items):"]
    lines.append("-" * 50)

    keys = list(data[0].keys()) if isinstance(data[0], dict) else []
    for item in data:
        name = item.get("username") or item.get("name") or "?"
        lines.append(f"\n  {name}:")
        for key in keys[:8]:
            val = item.get(key, "—")
            if isinstance(val, (int, float)):
                val = f"{val:,}"
            lines.append(f"    {key}: {val}")

    return "\n".join(lines)


def _analyze_trend(data, field):
    """Analyze trend over time."""
    if not field or not isinstance(data, list):
        return "Error: 'field' required for trend analysis"

    values = [_to_num(item.get(field)) for item in data if _to_num(item.get(field)) is not None]
    if len(values) < 3:
        return "Error: need at least 3 data points for trend analysis"

    lines = [f"📈 Trend of '{field}' ({len(values)} points):"]
    lines.append("-" * 40)

    first_half = values[:len(values) // 2]
    second_half = values[len(values) // 2:]

    avg_first = statistics.mean(first_half)
    avg_second = statistics.mean(second_half)
    change = ((avg_second - avg_first) / avg_first * 100) if avg_first else 0

    arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
    lines.append(f"  First half avg:  {avg_first:,.2f}")
    lines.append(f"  Second half avg: {avg_second:,.2f}")
    lines.append(f"  Change: {arrow} {change:+.1f}%")

    return "\n".join(lines)


def _to_num(val):
    """Convert value to number if possible."""
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        try:
            return float(val.replace(",", ""))
        except (ValueError, AttributeError):
            return None
    return None


def handle_create_chart(args: Dict) -> str:
    """Create chart using ASCII (no matplotlib dependency)."""
    chart_type = args.get("chart_type", "bar")
    title = args.get("title", "Chart")
    labels = args.get("labels", [])
    values = args.get("values", [])
    filename = args.get("filename", "chart.txt")

    if not labels or not values:
        return "Error: 'labels' and 'values' are required"

    if len(labels) != len(values):
        return f"Error: labels ({len(labels)}) and values ({len(values)}) must have equal length"

    try:
        # Generate ASCII chart
        max_val = max(values) if values else 1
        max_label_len = max(len(str(l)) for l in labels)

        lines = [f"  {title}", "  " + "=" * (max_label_len + 45)]

        if chart_type in ("bar", "horizontal_bar"):
            for label, val in zip(labels, values):
                bar_len = int((val / max_val) * 35) if max_val else 0
                bar = "█" * bar_len
                lines.append(f"  {str(label):>{max_label_len}s} │{bar} {val:,.0f}")

        elif chart_type == "line":
            lines.append("")
            # Simple sparkline
            for i, (label, val) in enumerate(zip(labels, values)):
                height = int((val / max_val) * 10) if max_val else 0
                marker = "─" * height + "●"
                lines.append(f"  {str(label):>{max_label_len}s} │{marker} {val:,.0f}")

        elif chart_type == "pie":
            total = sum(values)
            for label, val in sorted(zip(labels, values), key=lambda x: -x[1]):
                pct = (val / total * 100) if total else 0
                blocks = int(pct / 3)
                lines.append(f"  {str(label):>{max_label_len}s} │{'█' * blocks} {pct:.1f}% ({val:,.0f})")

        lines.append("  " + "=" * (max_label_len + 45))

        chart_text = "\n".join(lines)

        # Save to file
        if os.path.isabs(filename) or ".." in filename:
            return "Error: only relative file paths allowed"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(chart_text)

        return f"✅ Chart saved to '{filename}':\n\n{chart_text}"

    except Exception as e:
        return f"Error creating chart: {e}"
