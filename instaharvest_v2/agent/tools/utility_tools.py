"""
Utility Tools
=============
General-purpose utility tools for the AI agent:
JSON parsing, CSV conversion, math, text replacement,
file merging, and URL downloading.
"""

import csv
import io
import json
import math
import os
import re
import logging
import urllib.request
import urllib.error
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# JSON / CSV TOOLS
# ═══════════════════════════════════════════════════════════

def handle_json_parse(args: Dict, **kw) -> str:
    """Parse JSON string and return pretty-printed output."""
    text = args.get("text", args.get("json", "")).strip()
    if not text:
        return json.dumps({"error": "Parameter 'text' required — raw JSON string"})
    try:
        parsed = json.loads(text)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False, default=str)
        if len(pretty) > 5000:
            pretty = pretty[:5000] + "\n... (truncated)"
        return pretty
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})


def handle_csv_to_json(args: Dict, **kw) -> str:
    """Convert CSV file to JSON array."""
    filepath = args.get("path", args.get("file", "")).strip()
    delimiter = args.get("delimiter", ",")
    max_rows = min(args.get("max_rows", 500), 2000)

    if not filepath:
        return json.dumps({"error": "Parameter 'path' required"})

    try:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            return json.dumps({"error": f"File not found: {filepath}"})

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(dict(row))

        result = {
            "total_rows": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "data": rows,
        }
        output = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        if len(output) > 8000:
            # Truncate data but keep metadata
            result["data"] = rows[:20]
            result["note"] = f"Showing 20 of {len(rows)} rows"
            output = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        return output
    except Exception as e:
        return json.dumps({"error": f"CSV parse error: {e}"})


def handle_json_to_csv(args: Dict, **kw) -> str:
    """Convert JSON array to CSV file."""
    data = args.get("data", "")
    output_path = args.get("path", args.get("output", "")).strip()

    if not data:
        return json.dumps({"error": "Parameter 'data' required — JSON array string or list"})
    if not output_path:
        return json.dumps({"error": "Parameter 'path' required — output CSV file path"})

    try:
        # Parse if string
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data

        if not isinstance(parsed, list) or not parsed:
            return json.dumps({"error": "data must be a non-empty JSON array of objects"})

        output_path = os.path.abspath(output_path)
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Get all unique keys across all records
        all_keys = []
        seen = set()
        for row in parsed:
            if isinstance(row, dict):
                for k in row:
                    if k not in seen:
                        all_keys.append(k)
                        seen.add(k)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            for row in parsed:
                if isinstance(row, dict):
                    writer.writerow(row)

        size = os.path.getsize(output_path)
        return json.dumps({
            "status": "ok",
            "path": output_path,
            "rows": len(parsed),
            "columns": all_keys,
            "size_bytes": size,
        })
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"error": f"CSV write error: {e}"})


# ═══════════════════════════════════════════════════════════
# MATH / CALCULATE
# ═══════════════════════════════════════════════════════════

# Safe math functions for calculate tool
_SAFE_MATH = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "len": len, "int": int, "float": float, "str": str,
    "pow": pow, "divmod": divmod,
    # math module
    "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "True": True, "False": False,
}


def handle_calculate(args: Dict, **kw) -> str:
    """Safe math expression evaluator."""
    expression = args.get("expression", args.get("expr", "")).strip()
    if not expression:
        return json.dumps({"error": "Parameter 'expression' required"})

    # Block dangerous patterns
    blocked = ["import", "exec", "eval", "compile", "__", "open", "os.", "sys."]
    for b in blocked:
        if b in expression:
            return json.dumps({"error": f"Blocked pattern: '{b}'"})

    try:
        result = eval(expression, {"__builtins__": {}}, _SAFE_MATH)
        return json.dumps({
            "expression": expression,
            "result": result,
        }, default=str)
    except Exception as e:
        return json.dumps({"error": f"Calculation error: {e}"})


# ═══════════════════════════════════════════════════════════
# TEXT TOOLS
# ═══════════════════════════════════════════════════════════

def handle_text_replace(args: Dict, **kw) -> str:
    """Find and replace text in a file."""
    filepath = args.get("path", args.get("file", "")).strip()
    find = args.get("find", args.get("search", ""))
    replace = args.get("replace", args.get("replacement", ""))
    use_regex = args.get("regex", False)

    if not filepath:
        return json.dumps({"error": "Parameter 'path' required"})
    if not find:
        return json.dumps({"error": "Parameter 'find' required"})

    try:
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            return json.dumps({"error": f"File not found: {filepath}"})

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if use_regex:
            new_content, count = re.subn(find, replace, content)
        else:
            count = content.count(find)
            new_content = content.replace(find, replace)

        if count == 0:
            return json.dumps({"status": "no_match", "message": f"Pattern '{find}' not found in file"})

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        return json.dumps({
            "status": "ok",
            "replacements": count,
            "path": filepath,
        })
    except Exception as e:
        return json.dumps({"error": f"Replace error: {e}"})


def handle_merge_files(args: Dict, **kw) -> str:
    """Merge multiple files into one."""
    files = args.get("files", [])
    output_path = args.get("output", args.get("path", "")).strip()
    separator = args.get("separator", "\n")

    if not files or not isinstance(files, list):
        return json.dumps({"error": "Parameter 'files' required — list of file paths"})
    if not output_path:
        return json.dumps({"error": "Parameter 'output' required — output file path"})

    try:
        output_path = os.path.abspath(output_path)
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        parts = []
        for fp in files:
            fp = os.path.abspath(fp)
            if not os.path.exists(fp):
                return json.dumps({"error": f"File not found: {fp}"})
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                parts.append(f.read())

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(separator.join(parts))

        size = os.path.getsize(output_path)
        return json.dumps({
            "status": "ok",
            "merged_files": len(files),
            "output": output_path,
            "size_bytes": size,
        })
    except Exception as e:
        return json.dumps({"error": f"Merge error: {e}"})


# ═══════════════════════════════════════════════════════════
# DOWNLOAD URL
# ═══════════════════════════════════════════════════════════

def handle_download_url(args: Dict, **kw) -> str:
    """Download a file from URL to local path."""
    url = args.get("url", "").strip()
    output_path = args.get("path", args.get("output", "")).strip()

    if not url:
        return json.dumps({"error": "Parameter 'url' required"})

    # Default output filename from URL
    if not output_path:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or "download"
        output_path = filename

    # Block internal URLs
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.", "10.", "192.168.", "172.16."]
    for b in blocked:
        if b in url.lower():
            return json.dumps({"error": "Internal/local URLs are blocked"})

    try:
        output_path = os.path.abspath(output_path)
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "InstaHarvest-Agent/2.0")

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "unknown")

        # 50MB limit
        if len(data) > 50 * 1024 * 1024:
            return json.dumps({"error": "File too large (max 50MB)"})

        with open(output_path, "wb") as f:
            f.write(data)

        size = len(data)
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / 1024 / 1024:.2f} MB"

        return json.dumps({
            "status": "ok",
            "path": output_path,
            "size": size_str,
            "content_type": content_type,
        })
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"HTTP {e.code}: {e.reason}"})
    except urllib.error.URLError as e:
        return json.dumps({"error": f"URL error: {e.reason}"})
    except Exception as e:
        return json.dumps({"error": f"Download error: {e}"})
