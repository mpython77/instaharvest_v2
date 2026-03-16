"""
Pipeline Tools
==============
Agent tool handlers for pipeline, bulk download, AI suggestions, and comment management.
Covers: pipeline, bulk_download, ai_suggest, comment_manager API modules.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# PIPELINE — Data export to SQLite/JSONL
# ═══════════════════════════════════════════════════════════

def handle_pipeline_to_sqlite(args: Dict, ig=None, **kw) -> str:
    """Export pipeline data to SQLite database."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        db_path = args.get("db_path", "pipeline.db")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.pipeline.to_sqlite(username, db_path=db_path)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_pipeline_to_jsonl(args: Dict, ig=None, **kw) -> str:
    """Export pipeline data to JSONL file."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        output_path = args.get("output_path", "pipeline.jsonl")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.pipeline.to_jsonl(username, output_path=output_path)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# BULK DOWNLOAD (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_bulk_download_posts(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Bulk download all posts from a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for bulk download"})

    try:
        username = args.get("username", "")
        output_dir = args.get("output_dir", "downloads")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.bulk_download.all_posts(username, output_dir=output_dir)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_bulk_download_stories(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Bulk download all stories from a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for bulk download"})

    try:
        username = args.get("username", "")
        output_dir = args.get("output_dir", "downloads")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.bulk_download.all_stories(username, output_dir=output_dir)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_bulk_download_highlights(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Bulk download all highlights from a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for bulk download"})

    try:
        username = args.get("username", "")
        output_dir = args.get("output_dir", "downloads")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.bulk_download.all_highlights(username, output_dir=output_dir)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_bulk_download_everything(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Bulk download everything (posts, stories, highlights) from a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for bulk download"})

    try:
        username = args.get("username", "")
        output_dir = args.get("output_dir", "downloads")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.bulk_download.everything(username, output_dir=output_dir)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# AI SUGGEST — Hashtag/caption generation
# ═══════════════════════════════════════════════════════════

def handle_ai_suggest_hashtags(args: Dict, ig=None, **kw) -> str:
    """AI-powered hashtag suggestions from caption text."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        caption = args.get("caption", "")
        if not caption:
            return json.dumps({"error": "caption text is required"})

        result = ig.ai_suggest.hashtags_from_caption(caption)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_ai_suggest_captions(args: Dict, ig=None, **kw) -> str:
    """AI-powered caption ideas."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        topic = args.get("topic", "")
        style = args.get("style", "")
        if not topic:
            return json.dumps({"error": "topic is required"})

        result = ig.ai_suggest.caption_ideas(topic=topic, style=style)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# COMMENT MANAGER (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_manage_comments(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get comments for a media with filters."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for comment management"})

    try:
        media_id = args.get("media_id", "")
        max_count = args.get("max_count", 50)
        if not media_id:
            return json.dumps({"error": "media_id is required"})

        result = ig.comment_manager.get_comments(media_id, max_count=max_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_auto_reply_comments(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-reply to comments on a post."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for comment management"})

    try:
        media_id = args.get("media_id", "")
        reply = args.get("reply", "")
        max_count = args.get("max_count", 10)
        if not media_id or not reply:
            return json.dumps({"error": "media_id and reply text are required"})

        result = ig.comment_manager.auto_reply(
            media_id, reply=reply, max_count=max_count
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_delete_spam_comments(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Delete spam comments from a post."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for comment management"})

    try:
        media_id = args.get("media_id", "")
        if not media_id:
            return json.dumps({"error": "media_id is required"})

        result = ig.comment_manager.delete_spam(media_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_comment_sentiment(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Analyze sentiment of comments on a post."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for comment management"})

    try:
        media_id = args.get("media_id", "")
        if not media_id:
            return json.dumps({"error": "media_id is required"})

        result = ig.comment_manager.sentiment(media_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
