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

        result = ig.automation.dm_new_followers(message=message, max_count=max_count)
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
            hashtag=hashtag, comment=comment, max_count=max_count
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
        result = ig.automation.auto_like_feed(max_count=max_count)
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

        result = ig.automation.auto_like_hashtag(hashtag=hashtag, max_count=max_count)
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
        max_count = args.get("max_count", 20)
        result = ig.automation.watch_stories(max_count=max_count)
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
        result = ig.automation.action_log()
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
            image_path=image_path, caption=caption, schedule_time=schedule_time
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

        result = ig.scheduler.story_at(
            media_path=media_path, schedule_time=schedule_time
        )
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
            video_path=video_path, caption=caption, schedule_time=schedule_time
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

        result = ig.monitor.watch(username)
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
        if username:
            result = ig.monitor.event_log(username=username)
        else:
            result = ig.monitor.event_log()
        return json.dumps(result, default=str)
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
