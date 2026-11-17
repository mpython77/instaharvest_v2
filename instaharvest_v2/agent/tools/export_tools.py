"""
Export & Pipeline Tools
=======================
Data export handlers: CSV, JSON, JSONL, SQLite.
"""

import json
import logging
import os
import re
import sqlite3
from typing import Any, Dict, Optional

logger = logging.getLogger("instaharvest_v2.agent.tools")


def _validate_safe_path(filename: str) -> Optional[str]:
    """Validate relative filename stays inside the working directory."""
    if not filename or os.path.isabs(filename) or ".." in filename:
        return "Error: only relative paths inside working directory are allowed."
    cwd = os.path.abspath(os.getcwd())
    resolved = os.path.abspath(os.path.join(cwd, filename))
    if not resolved.startswith(cwd + os.sep) and resolved != cwd:
        return "Error: access outside working directory is forbidden."
    return None


def _try_parse_structured_data(data: Any):
    """Return parsed dict/list if data is structured JSON/collection, else None."""
    if isinstance(data, (dict, list)):
        return data
    if isinstance(data, str):
        stripped = data.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def handle_export_followers_csv(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Export a user's followers to CSV file."""
    if not is_logged_in:
        return "❌ Login required to export followers."
    username = args.get("username", "").strip().lstrip("@").lower()
    filename = args.get("filename", f"{username}_followers.csv")
    max_count = min(args.get("max_count", 200), 5000)
    if not username:
        return "Error: 'username' is required."
    try:
        result = ig.export.followers_to_csv(username, output_path=filename, max_count=max_count)
        return f"✅ Followers exported to {filename}! {str(result)[:200] if result else ''}"
    except Exception as e:
        return f"Error exporting followers: {e}"


def handle_export_following_csv(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Export a user's following to CSV file."""
    if not is_logged_in:
        return "❌ Login required to export following."
    username = args.get("username", "").strip().lstrip("@").lower()
    filename = args.get("filename", f"{username}_following.csv")
    max_count = min(args.get("max_count", 200), 5000)
    if not username:
        return "Error: 'username' is required."
    try:
        result = ig.export.following_to_csv(username, output_path=filename, max_count=max_count)
        return f"✅ Following exported to {filename}! {str(result)[:200] if result else ''}"
    except Exception as e:
        return f"Error exporting following: {e}"


def handle_export_post_likers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Export likers of a post to file."""
    if not is_logged_in:
        return "❌ Login required to export likers."
    media_id = args.get("media_id", "")
    filename = args.get("filename", "post_likers.csv")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        result = ig.export.post_likers(media_id, output_path=filename)
        return f"✅ Post likers exported to {filename}! {str(result)[:200] if result else ''}"
    except Exception as e:
        return f"Error exporting post likers: {e}"


def handle_export_to_json(args: Dict, ig=None, **kw) -> str:
    """Export structured data or a user profile/dataset to JSON file."""
    data = args.get("data", "")
    filename = args.get("filename", "export.json")
    if not data:
        return "Error: 'data' is required."
    path_err = _validate_safe_path(filename)
    if path_err:
        return path_err
    try:
        parsed = _try_parse_structured_data(data)
        if parsed is not None:
            parent = os.path.dirname(os.path.abspath(filename))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2, default=str)
            return f"✅ Data exported to {filename}!"
        if ig is None:
            return "Error: Instagram instance not available for username export."
        username = str(data).strip().lstrip("@").lower()
        ig.export.to_json(username, output_path=filename)
        return f"✅ Data exported to {filename}!"
    except Exception as e:
        return f"Error exporting to JSON: {e}"


def handle_save_to_sqlite(args: Dict, ig=None, **kw) -> str:
    """Save structured records or a user dataset to SQLite database."""
    data = args.get("data", "")
    db_name = args.get("db_name", "instagram_data.db")
    table_name = args.get("table_name", "data")
    if not data:
        return "Error: 'data' is required."
    path_err = _validate_safe_path(db_name)
    if path_err:
        return path_err
    try:
        parsed = _try_parse_structured_data(data)
        if parsed is not None:
            safe_table = re.sub(r"[^a-zA-Z0-9_]", "_", str(table_name or "data"))
            if not safe_table or safe_table[0].isdigit():
                safe_table = f"t_{safe_table}"
            rows = parsed if isinstance(parsed, list) else [parsed]
            normalized = [r if isinstance(r, dict) else {"value": r} for r in rows]
            if not normalized:
                return "Error: no rows to insert."
            columns = []
            for row in normalized:
                for k in row.keys():
                    col = re.sub(r"[^a-zA-Z0-9_]", "_", str(k)) or "col"
                    if col not in columns:
                        columns.append(col)
            parent = os.path.dirname(os.path.abspath(db_name))
            if parent:
                os.makedirs(parent, exist_ok=True)
            conn = sqlite3.connect(db_name)
            try:
                col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
                conn.execute(f'CREATE TABLE IF NOT EXISTS "{safe_table}" ({col_defs})')
                placeholders = ", ".join("?" for _ in columns)
                col_names = ", ".join(f'"{c}"' for c in columns)
                for row in normalized:
                    vals = [
                        json.dumps(v, default=str) if isinstance(v := row.get(c), (dict, list)) else ("" if v is None else str(v))
                        for c in columns
                    ]
                    conn.execute(f'INSERT INTO "{safe_table}" ({col_names}) VALUES ({placeholders})', vals)
                conn.commit()
            finally:
                conn.close()
            return f"✅ Data saved to SQLite ({db_name}, table: {safe_table})!"
        if ig is None:
            return "Error: Instagram instance not available for username SQLite pipeline."
        username = str(data).strip().lstrip("@").lower()
        ig.pipeline.to_sqlite(username, db_path=db_name)
        return f"✅ Data saved to SQLite ({db_name}, table: {table_name})!"
    except Exception as e:
        return f"Error saving to SQLite: {e}"


def handle_save_to_jsonl(args: Dict, ig=None, **kw) -> str:
    """Save structured records or a user dataset to JSONL (JSON Lines) format."""
    data = args.get("data", "")
    filename = args.get("filename", "export.jsonl")
    if not data:
        return "Error: 'data' is required."
    path_err = _validate_safe_path(filename)
    if path_err:
        return path_err
    try:
        parsed = _try_parse_structured_data(data)
        if parsed is not None:
            rows = parsed if isinstance(parsed, list) else [parsed]
            parent = os.path.dirname(os.path.abspath(filename))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            return f"✅ Data saved to JSONL ({filename})!"
        if ig is None:
            return "Error: Instagram instance not available for username JSONL pipeline."
        username = str(data).strip().lstrip("@").lower()
        ig.pipeline.to_jsonl(username, output_path=filename)
        return f"✅ Data saved to JSONL ({filename})!"
    except Exception as e:
        return f"Error saving to JSONL: {e}"
