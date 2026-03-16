"""
Export & Pipeline Tools
=======================
Data export handlers: CSV, JSON, JSONL, SQLite.
"""

import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


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
        result = ig.export.followers_to_csv(username, filename=filename, max_count=max_count)
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
        result = ig.export.following_to_csv(username, filename=filename, max_count=max_count)
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
        result = ig.export.post_likers(media_id, filename=filename)
        return f"✅ Post likers exported to {filename}! {str(result)[:200] if result else ''}"
    except Exception as e:
        return f"Error exporting post likers: {e}"


def handle_export_to_json(args: Dict, ig=None, **kw) -> str:
    """Export data to JSON file."""
    data = args.get("data", "")
    filename = args.get("filename", "export.json")
    if not data:
        return "Error: 'data' is required."
    try:
        result = ig.export.to_json(data, filename=filename)
        return f"✅ Data exported to {filename}!"
    except Exception as e:
        return f"Error exporting to JSON: {e}"


def handle_save_to_sqlite(args: Dict, ig=None, **kw) -> str:
    """Save data to SQLite database."""
    data = args.get("data", "")
    db_name = args.get("db_name", "instagram_data.db")
    table_name = args.get("table_name", "data")
    if not data:
        return "Error: 'data' is required."
    try:
        result = ig.pipeline.to_sqlite(data, db_name=db_name, table_name=table_name)
        return f"✅ Data saved to SQLite ({db_name}, table: {table_name})!"
    except Exception as e:
        return f"Error saving to SQLite: {e}"


def handle_save_to_jsonl(args: Dict, ig=None, **kw) -> str:
    """Save data to JSONL (JSON Lines) format."""
    data = args.get("data", "")
    filename = args.get("filename", "export.jsonl")
    if not data:
        return "Error: 'data' is required."
    try:
        result = ig.pipeline.to_jsonl(data, filename=filename)
        return f"✅ Data saved to JSONL ({filename})!"
    except Exception as e:
        return f"Error saving to JSONL: {e}"
