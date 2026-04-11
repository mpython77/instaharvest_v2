"""
System Tools
============
File management, directory operations, session persistence,
and system information handlers.

These give the AI agent full file-system awareness so it can
read, write, navigate, and persist data autonomously.
"""

import glob
import json
import os
import platform
import shutil
import time
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")

# Session data lives in ~/.instaharvest_v2/agent_sessions/
_SESSIONS_DIR = os.path.join(
    os.path.expanduser("~"), ".instaharvest_v2", "agent_sessions"
)


# ═══════════════════════════════════════════════════════════
# FILE I/O — Enhanced (7 tools)
# ═══════════════════════════════════════════════════════════

def handle_write_file(args: Dict, **kw) -> str:
    """Write content to a file (creates dirs automatically)."""
    filepath = args.get("path", args.get("filename", "")).strip()
    content = args.get("content", "")
    encoding = args.get("encoding", "utf-8")

    if not filepath:
        return "Error: 'path' is required."

    try:
        # Resolve to absolute path
        filepath = os.path.abspath(filepath)
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)

        size = os.path.getsize(filepath)
        return f"✅ File written: {filepath}\n   Size: {size:,} bytes ({len(content):,} chars)"
    except Exception as e:
        return f"Error writing file: {e}"


def handle_append_to_file(args: Dict, **kw) -> str:
    """Append content to an existing file."""
    filepath = args.get("path", args.get("filename", "")).strip()
    content = args.get("content", "")

    if not filepath:
        return "Error: 'path' is required."
    if not content:
        return "Error: 'content' is required."

    try:
        filepath = os.path.abspath(filepath)
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content)

        size = os.path.getsize(filepath)
        return f"✅ Appended {len(content):,} chars to: {filepath}\n   Total size: {size:,} bytes"
    except Exception as e:
        return f"Error appending to file: {e}"


def handle_copy_file(args: Dict, **kw) -> str:
    """Copy a file to a new location."""
    src = args.get("source", args.get("src", "")).strip()
    dst = args.get("destination", args.get("dst", "")).strip()

    if not src or not dst:
        return "Error: 'source' and 'destination' are required."

    try:
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)

        if not os.path.exists(src):
            return f"Error: source not found: {src}"

        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)

        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        return f"✅ Copied: {src}\n   → {dst} ({size:,} bytes)"
    except Exception as e:
        return f"Error copying file: {e}"


def handle_move_file(args: Dict, **kw) -> str:
    """Move or rename a file."""
    src = args.get("source", args.get("src", "")).strip()
    dst = args.get("destination", args.get("dst", "")).strip()

    if not src or not dst:
        return "Error: 'source' and 'destination' are required."

    try:
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)

        if not os.path.exists(src):
            return f"Error: source not found: {src}"

        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)

        shutil.move(src, dst)
        return f"✅ Moved: {src}\n   → {dst}"
    except Exception as e:
        return f"Error moving file: {e}"


def handle_delete_file(args: Dict, **kw) -> str:
    """Delete a file or empty directory."""
    filepath = args.get("path", "").strip()

    if not filepath:
        return "Error: 'path' is required."

    try:
        filepath = os.path.abspath(filepath)

        if not os.path.exists(filepath):
            return f"Error: not found: {filepath}"

        if os.path.isdir(filepath):
            if os.listdir(filepath):
                return f"Error: directory not empty: {filepath} (use force=true to delete recursively)"
            os.rmdir(filepath)
            return f"✅ Directory deleted: {filepath}"
        else:
            os.remove(filepath)
            return f"✅ File deleted: {filepath}"
    except Exception as e:
        return f"Error deleting: {e}"


def handle_file_exists(args: Dict, **kw) -> str:
    """Check if a file or directory exists."""
    filepath = args.get("path", "").strip()

    if not filepath:
        return "Error: 'path' is required."

    filepath = os.path.abspath(filepath)
    exists = os.path.exists(filepath)
    is_file = os.path.isfile(filepath)
    is_dir = os.path.isdir(filepath)

    if exists:
        kind = "📄 file" if is_file else "📁 directory"
        return f"✅ EXISTS — {kind}: {filepath}"
    else:
        return f"❌ NOT FOUND: {filepath}"


def handle_get_file_info(args: Dict, **kw) -> str:
    """Get detailed file information: size, type, timestamps."""
    filepath = args.get("path", "").strip()

    if not filepath:
        return "Error: 'path' is required."

    filepath = os.path.abspath(filepath)

    if not os.path.exists(filepath):
        return f"Error: not found: {filepath}"

    try:
        stat = os.stat(filepath)
        is_dir = os.path.isdir(filepath)
        kind = "Directory" if is_dir else "File"
        ext = os.path.splitext(filepath)[1] if not is_dir else ""

        size = stat.st_size
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size / 1024 / 1024:.2f} MB"

        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"📋 File Info: {filepath}",
            f"  Type: {kind}{f' ({ext})' if ext else ''}",
            f"  Size: {size_str}",
            f"  Modified: {modified}",
            f"  Created: {created}",
        ]

        if is_dir:
            items = os.listdir(filepath)
            lines.append(f"  Items: {len(items)}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting file info: {e}"


# ═══════════════════════════════════════════════════════════
# DIRECTORY OPERATIONS (4 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_working_directory(args: Dict, **kw) -> str:
    """Get current working directory."""
    cwd = os.getcwd()
    items = os.listdir(cwd)
    dirs = [x for x in items if os.path.isdir(os.path.join(cwd, x))]
    files = [x for x in items if os.path.isfile(os.path.join(cwd, x))]

    lines = [
        f"📂 Working Directory: {cwd}",
        f"   Contains: {len(dirs)} directories, {len(files)} files",
    ]

    # Show top-level contents
    if dirs:
        lines.append(f"   📁 Dirs: {', '.join(sorted(dirs)[:15])}")
    if files:
        lines.append(f"   📄 Files: {', '.join(sorted(files)[:15])}")

    return "\n".join(lines)


def handle_create_directory(args: Dict, **kw) -> str:
    """Create a directory (including parent directories)."""
    dirpath = args.get("path", "").strip()

    if not dirpath:
        return "Error: 'path' is required."

    try:
        dirpath = os.path.abspath(dirpath)
        os.makedirs(dirpath, exist_ok=True)
        return f"✅ Directory created: {dirpath}"
    except Exception as e:
        return f"Error creating directory: {e}"


def handle_list_directory(args: Dict, **kw) -> str:
    """List directory contents with details (size, type, count)."""
    dirpath = args.get("path", args.get("directory", ".")).strip()
    pattern = args.get("pattern", "").strip()
    recursive = args.get("recursive", False)
    max_items = min(args.get("max_items", 50), 200)

    try:
        dirpath = os.path.abspath(dirpath)

        if not os.path.isdir(dirpath):
            return f"Error: not a directory: {dirpath}"

        if pattern:
            if recursive:
                search = os.path.join(dirpath, "**", pattern)
                entries = glob.glob(search, recursive=True)
            else:
                search = os.path.join(dirpath, pattern)
                entries = glob.glob(search)
        else:
            entries = [os.path.join(dirpath, x) for x in os.listdir(dirpath)]

        entries = sorted(entries)[:max_items]

        if not entries:
            return f"Empty directory: {dirpath}" + (f" (pattern: {pattern})" if pattern else "")

        lines = [f"📂 {dirpath}" + (f"  [pattern: {pattern}]" if pattern else "")]
        lines.append("─" * 50)

        dirs_list = []
        files_list = []

        for entry in entries:
            name = os.path.relpath(entry, dirpath)
            if os.path.isdir(entry):
                try:
                    count = len(os.listdir(entry))
                except PermissionError:
                    count = "?"
                dirs_list.append(f"  📁 {name}/  ({count} items)")
            else:
                size = os.path.getsize(entry)
                if size < 1024:
                    s = f"{size}B"
                elif size < 1024 * 1024:
                    s = f"{size / 1024:.1f}KB"
                else:
                    s = f"{size / 1024 / 1024:.1f}MB"
                files_list.append(f"  📄 {name}  ({s})")

        lines.extend(dirs_list)
        lines.extend(files_list)
        lines.append(f"\nTotal: {len(dirs_list)} dirs, {len(files_list)} files")

        if len(entries) >= max_items:
            lines.append(f"⚠️ Showing first {max_items} items only")

        return "\n".join(lines)
    except Exception as e:
        return f"Error listing directory: {e}"


def handle_find_files(args: Dict, **kw) -> str:
    """Search for files by glob pattern (recursive)."""
    pattern = args.get("pattern", "").strip()
    directory = args.get("directory", ".").strip()
    max_results = min(args.get("max_results", 30), 100)

    if not pattern:
        return "Error: 'pattern' is required (e.g. '*.json', '**/*.py', 'data_*')."

    try:
        directory = os.path.abspath(directory)
        search_path = os.path.join(directory, pattern)
        results = glob.glob(search_path, recursive=True)

        if not results:
            return f"No files matching '{pattern}' in {directory}"

        results = sorted(results)[:max_results]

        lines = [f"🔍 Found {len(results)} match(es) for '{pattern}' in {directory}:"]
        for i, path in enumerate(results, 1):
            rel = os.path.relpath(path, directory)
            size = os.path.getsize(path) if os.path.isfile(path) else 0
            if size < 1024:
                s = f"{size}B"
            elif size < 1024 * 1024:
                s = f"{size / 1024:.1f}KB"
            else:
                s = f"{size / 1024 / 1024:.1f}MB"
            kind = "📁" if os.path.isdir(path) else "📄"
            lines.append(f"  {i}. {kind} {rel}  ({s})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error finding files: {e}"


# ═══════════════════════════════════════════════════════════
# SESSION & DATA PERSISTENCE (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_save_session_data(args: Dict, **kw) -> str:
    """Save JSON data to a named session file for later retrieval."""
    name = args.get("name", "").strip()
    data = args.get("data", "")

    if not name:
        return "Error: 'name' is required (e.g. 'user_list', 'config', 'target_accounts')."
    if not data:
        return "Error: 'data' is required (any JSON-serializable content)."

    try:
        os.makedirs(_SESSIONS_DIR, exist_ok=True)

        # Ensure name is safe
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").rstrip()
        if not safe_name:
            return "Error: invalid session name."

        filepath = os.path.join(_SESSIONS_DIR, f"{safe_name}.json")

        # Parse data if it's a string, or use directly
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                parsed = {"text": data}
        else:
            parsed = data

        session_obj = {
            "name": safe_name,
            "saved_at": datetime.now().isoformat(),
            "data": parsed,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_obj, f, indent=2, ensure_ascii=False, default=str)

        size = os.path.getsize(filepath)
        return f"✅ Session saved: '{safe_name}'\n   Path: {filepath}\n   Size: {size:,} bytes"
    except Exception as e:
        return f"Error saving session: {e}"


def handle_load_session_data(args: Dict, **kw) -> str:
    """Load previously saved session data by name."""
    name = args.get("name", "").strip()

    if not name:
        return "Error: 'name' is required."

    safe_name = "".join(c for c in name if c.isalnum() or c in "-_").rstrip()
    filepath = os.path.join(_SESSIONS_DIR, f"{safe_name}.json")

    if not os.path.exists(filepath):
        # Try to find similar sessions
        available = _list_session_names()
        if available:
            return f"Error: session '{safe_name}' not found.\nAvailable sessions: {', '.join(available)}"
        return f"Error: session '{safe_name}' not found. No saved sessions exist."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            session_obj = json.load(f)

        saved_at = session_obj.get("saved_at", "unknown")
        data = session_obj.get("data", {})

        # Format output
        data_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        if len(data_str) > 3000:
            data_str = data_str[:3000] + "\n... (truncated)"

        return f"📂 Session loaded: '{safe_name}' (saved: {saved_at})\n{data_str}"
    except Exception as e:
        return f"Error loading session: {e}"


def _list_session_names() -> list:
    """List available session names."""
    if not os.path.isdir(_SESSIONS_DIR):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(_SESSIONS_DIR)
        if f.endswith(".json")
    ]


def handle_list_sessions(args: Dict, **kw) -> str:
    """List all saved session files."""
    if not os.path.isdir(_SESSIONS_DIR):
        return "No saved sessions found."

    sessions = []
    for filename in sorted(os.listdir(_SESSIONS_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(_SESSIONS_DIR, filename)
        try:
            size = os.path.getsize(filepath)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")
            name = os.path.splitext(filename)[0]
            sessions.append(f"  📄 {name}  ({size:,} bytes, {mtime})")
        except Exception as e:
            sessions.append(f"  📄 {os.path.splitext(filename)[0]}  (error reading)")

    if not sessions:
        return "No saved sessions found."

    lines = [f"💾 Saved Sessions ({len(sessions)}):"]
    lines.append("─" * 40)
    lines.extend(sessions)
    lines.append(f"\nDirectory: {_SESSIONS_DIR}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# ENVIRONMENT & SYSTEM (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_env_var(args: Dict, **kw) -> str:
    """Read an environment variable value."""
    name = args.get("name", "").strip()

    if not name:
        return "Error: 'name' is required (e.g. 'PATH', 'HOME', 'USERPROFILE')."

    # Block sensitive vars
    blocked = {"password", "secret", "token", "api_key", "private_key", "credentials"}
    if name.lower() in blocked or any(b in name.lower() for b in blocked):
        return f"⚠️ Access to '{name}' is blocked for security reasons."

    value = os.environ.get(name)
    if value is None:
        return f"❌ Environment variable '{name}' is not set."

    # Truncate very long values
    if len(value) > 500:
        value = value[:500] + "..."

    return f"🔧 {name} = {value}"


def handle_set_working_directory(args: Dict, **kw) -> str:
    """Change the current working directory."""
    dirpath = args.get("path", "").strip()

    if not dirpath:
        return "Error: 'path' is required."

    try:
        dirpath = os.path.abspath(dirpath)

        if not os.path.isdir(dirpath):
            return f"Error: not a directory: {dirpath}"

        os.chdir(dirpath)
        items = os.listdir(dirpath)
        return f"✅ Working directory changed to: {dirpath}\n   Contents: {len(items)} items"
    except Exception as e:
        return f"Error changing directory: {e}"


def handle_get_system_info(args: Dict, **kw) -> str:
    """Get system information: OS, Python version, cwd, disk space."""
    try:
        cwd = os.getcwd()
        home = os.path.expanduser("~")

        # Disk space
        try:
            total, used, free = shutil.disk_usage(cwd)
            disk_info = (
                f"  Disk (cwd): {total / (1024**3):.1f} GB total, "
                f"{used / (1024**3):.1f} GB used, "
                f"{free / (1024**3):.1f} GB free"
            )
        except Exception as e:
            disk_info = "  Disk: N/A"

        lines = [
            "🖥️ System Info:",
            f"  OS: {platform.system()} {platform.release()} ({platform.machine()})",
            f"  Python: {platform.python_version()}",
            f"  Home: {home}",
            f"  Working Directory: {cwd}",
            disk_info,
            f"  CPU: {os.cpu_count()} cores",
            f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        # Sessions directory
        if os.path.isdir(_SESSIONS_DIR):
            session_count = len([f for f in os.listdir(_SESSIONS_DIR) if f.endswith(".json")])
            lines.append(f"  Sessions: {session_count} saved")
        else:
            lines.append("  Sessions: none")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting system info: {e}"
