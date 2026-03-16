"""
File Tools
==========
File I/O handlers: read_file, list_files.
"""

import csv
import glob
import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


def handle_read_file(args: Dict) -> str:
    """Read file contents from current directory."""
    filename = args.get("filename", "")
    max_lines = min(args.get("max_lines", 100), 500)

    if not filename:
        return "Error: no filename provided"

    # Security: only relative paths
    if os.path.isabs(filename) or ".." in filename:
        return "Error: only relative paths allowed (no absolute paths or '..')"

    if not os.path.exists(filename):
        return f"Error: file not found: '{filename}'"

    try:
        ext = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(filename)

        if file_size > 5 * 1024 * 1024:  # 5MB limit
            return f"Error: file too large ({file_size / 1024 / 1024:.1f}MB). Max: 5MB"

        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            if ext == ".json":
                data = json.load(f)
                content = json.dumps(data, indent=2, ensure_ascii=False)
                lines = content.split("\n")
                if len(lines) > max_lines:
                    lines = lines[:max_lines]
                    lines.append(f"... (truncated, {len(content)} chars total)")
                return "\n".join(lines)

            elif ext in (".csv", ".tsv"):
                delimiter = "\t" if ext == ".tsv" else ","
                reader = csv.reader(f, delimiter=delimiter)
                rows = []
                for i, row in enumerate(reader):
                    if i >= max_lines:
                        rows.append(f"... (truncated at {max_lines} rows)")
                        break
                    rows.append(delimiter.join(row))
                return "\n".join(rows)

            else:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncated at {max_lines} lines)")
                        break
                    lines.append(line.rstrip())
                return "\n".join(lines)

    except Exception as e:
        return f"Error reading file: {e}"


def handle_list_files(args: Dict) -> str:
    """List files in directory."""
    directory = args.get("directory", ".")
    pattern = args.get("pattern", "*")

    # Security
    if os.path.isabs(directory) or ".." in directory:
        return "Error: only relative paths allowed"

    if not os.path.isdir(directory):
        return f"Error: directory not found: '{directory}'"

    try:
        search_path = os.path.join(directory, pattern)
        entries = glob.glob(search_path)

        if not entries:
            return f"No files matching '{pattern}' in '{directory}'"

        lines = [f"Files in '{directory}' (pattern: {pattern}):"]
        lines.append("-" * 50)

        dirs = []
        files = []

        for entry in sorted(entries):
            if os.path.isdir(entry):
                child_count = len(os.listdir(entry))
                dirs.append(f"  📁 {os.path.basename(entry)}/  ({child_count} items)")
            else:
                size = os.path.getsize(entry)
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f}KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f}MB"
                files.append(f"  📄 {os.path.basename(entry)}  ({size_str})")

        lines.extend(dirs)
        lines.extend(files)
        lines.append(f"\nTotal: {len(dirs)} dirs, {len(files)} files")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing files: {e}"
