"""
Automation Tools
================
Agent tool handlers for automation, scheduling, and monitoring.
Covers: automation, scheduler, monitor API modules.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# AUTOMATION — Auto-DM, auto-like, auto-comment (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def _read_attr_or_call(obj, attr_name: str):
    """Read a property/attribute or invoke it safely if callable (supports mocks)."""
    val = getattr(obj, attr_name)
    return val() if callable(val) else val


def _extract_tray_usernames(tray_data) -> list:
    """Extract unique usernames from a get_reels_tray() payload."""
    if not isinstance(tray_data, dict):
        return []
    usernames = []
    for entry in tray_data.get("tray", []):
        if isinstance(entry, dict):
            user = entry.get("user") or {}
            uname = user.get("username")
            if uname and uname not in usernames:
                usernames.append(uname)
    return usernames


def handle_auto_dm_new_followers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-DM new followers."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        message = args.get("message", "")
        max_count = args.get("max_count", 10)
        if not message:
            return json.dumps({"error": "message text is required"})

        result = ig.automation.dm_new_followers(templates=message, max_count=max_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_auto_comment_hashtag(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-comment on hashtag posts."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        hashtag = args.get("hashtag", "")
        comment = args.get("comment", "")
        max_count = args.get("max_count", 5)
        if not hashtag or not comment:
            return json.dumps({"error": "hashtag and comment are required"})

        result = ig.automation.comment_on_hashtag(
            tag=hashtag, templates=[comment], count=max_count
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_auto_like_feed(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-like posts from timeline feed."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        max_count = args.get("max_count", 10)
        result = ig.automation.auto_like_feed(count=max_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_auto_like_hashtag(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-like posts from a hashtag."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        hashtag = args.get("hashtag", "")
        max_count = args.get("max_count", 10)
        if not hashtag:
            return json.dumps({"error": "hashtag is required"})

        result = ig.automation.auto_like_hashtag(tag=hashtag, count=max_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_auto_watch_stories(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Auto-watch stories from following."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        username = args.get("username", "").strip().lstrip("@")
        max_count = args.get("max_count", 20)
        if username:
            result = ig.automation.watch_stories(username)
        else:
            tray = ig.stories.get_reels_tray() if hasattr(ig, "stories") else {}
            if isinstance(tray, dict):
                targets = _extract_tray_usernames(tray)[:max_count]
                watched_total = 0
                watched_users = []
                for uname in targets:
                    res = ig.automation.watch_stories(uname)
                    count_seen = res.get("watched", 0) if isinstance(res, dict) else 0
                    watched_total += count_seen
                    watched_users.append(uname)
                result = {"watched": watched_total, "accounts": watched_users}
            else:
                result = ig.automation.watch_stories("")
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_action_log(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get automation action log."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for automation"})

    try:
        result = _read_attr_or_call(ig.automation, "action_log")
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# SCHEDULER — Post/story/reel scheduling (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_schedule_post(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Schedule a post for later."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for scheduling"})

    try:
        image_path = args.get("image_path", "")
        caption = args.get("caption", "")
        schedule_time = args.get("schedule_time", "")
        if not image_path or not schedule_time:
            return json.dumps({"error": "image_path and schedule_time are required"})

        result = ig.scheduler.post_at(
            scheduled_time=schedule_time, photo=image_path, caption=caption
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_schedule_story(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Schedule a story for later."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for scheduling"})

    try:
        media_path = args.get("media_path", "")
        schedule_time = args.get("schedule_time", "")
        if not media_path or not schedule_time:
            return json.dumps({"error": "media_path and schedule_time are required"})

        is_video = media_path.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))
        media_kw = {"video": media_path} if is_video else {"photo": media_path}
        result = ig.scheduler.story_at(scheduled_time=schedule_time, **media_kw)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_schedule_reel(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Schedule a reel for later."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for scheduling"})

    try:
        video_path = args.get("video_path", "")
        caption = args.get("caption", "")
        schedule_time = args.get("schedule_time", "")
        if not video_path or not schedule_time:
            return json.dumps({"error": "video_path and schedule_time are required"})

        result = ig.scheduler.reel_at(
            scheduled_time=schedule_time, video=video_path, caption=caption
        )
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_list_scheduled_jobs(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """List all scheduled jobs."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for scheduling"})

    try:
        result = ig.scheduler.list_jobs()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_cancel_scheduled_job(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Cancel a scheduled job."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for scheduling"})

    try:
        job_id = args.get("job_id", "")
        if not job_id:
            return json.dumps({"error": "job_id is required"})

        result = ig.scheduler.cancel(job_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# MONITOR — Account watching & change detection (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_monitor_account(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Start monitoring an account for changes."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for monitoring"})

    try:
        username = args.get("username", "")
        if not username:
            return json.dumps({"error": "username is required"})

        watcher = ig.monitor.watch(username)
        if isinstance(watcher, dict):
            result = watcher
        else:
            watched_list = (
                _read_attr_or_call(ig.monitor, "watched_accounts")
                if hasattr(ig.monitor, "watched_accounts")
                else [username]
            )
            result = {
                "watching": getattr(watcher, "username", username),
                "status": "watching",
                "watched_accounts": watched_list,
            }
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_unmonitor_account(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Stop monitoring an account."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for monitoring"})

    try:
        username = args.get("username", "")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.monitor.unwatch(username)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_monitor_check_now(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Force check all monitored accounts now."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for monitoring"})

    try:
        result = ig.monitor.check_now()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_monitor_events(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get monitoring event log."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for monitoring"})

    try:
        username = args.get("username", None)
        events = _read_attr_or_call(ig.monitor, "event_log")
        if username and isinstance(events, list):
            target_user = username.lstrip("@").lower()
            events = [
                e for e in events
                if isinstance(e, dict) and str(e.get("username", "")).lower() == target_user
            ]
        return json.dumps(events, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_monitor_stats(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get monitoring statistics."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for monitoring"})

    try:
        result = ig.monitor.get_stats()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
