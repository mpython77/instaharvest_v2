"""
Growth Tools
============
Account growth and audience management handlers.
"""

import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


def handle_get_non_followers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get users you follow who don't follow you back."""
    if not is_logged_in:
        return "❌ Login required to check non-followers."
    try:
        result = ig.growth.get_non_followers()
        if not result:
            return "Everyone you follow follows you back! 🎉"
        items = result if isinstance(result, list) else [result]
        lines = [f"👻 Non-followers ({len(items)} users don't follow you back):"]
        for i, u in enumerate(items[:30], 1):
            if isinstance(u, dict):
                uname = u.get("username", "?")
                fname = u.get("full_name", "")
                lines.append(f"  {i}. @{uname} — {fname}")
            else:
                lines.append(f"  {i}. @{u}")
        if len(items) > 30:
            lines.append(f"  ... and {len(items) - 30} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting non-followers: {e}"


def handle_get_fans(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get fans — users who follow you but you don't follow back."""
    if not is_logged_in:
        return "❌ Login required to check fans."
    try:
        result = ig.growth.get_fans()
        if not result:
            return "No fans found (you follow everyone who follows you)."
        items = result if isinstance(result, list) else [result]
        lines = [f"🌟 Fans ({len(items)} users follow you but you don't follow back):"]
        for i, u in enumerate(items[:30], 1):
            if isinstance(u, dict):
                uname = u.get("username", "?")
                fname = u.get("full_name", "")
                lines.append(f"  {i}. @{uname} — {fname}")
            else:
                lines.append(f"  {i}. @{u}")
        if len(items) > 30:
            lines.append(f"  ... and {len(items) - 30} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting fans: {e}"


def handle_unfollow_non_followers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Unfollow all users who don't follow you back."""
    if not is_logged_in:
        return "❌ Login required to unfollow users."
    max_count = min(args.get("max_count", 10), 50)
    try:
        result = ig.growth.unfollow_non_followers(max_count=max_count)
        if isinstance(result, dict):
            unfollowed = result.get("unfollowed", 0)
            return f"✅ Unfollowed {unfollowed} non-followers!"
        return f"✅ Unfollow non-followers completed! Result: {str(result)[:200]}"
    except Exception as e:
        return f"Error unfollowing non-followers: {e}"


def handle_follow_hashtag_users(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Follow users who posted with a specific hashtag."""
    if not is_logged_in:
        return "❌ Login required to follow users."
    hashtag = args.get("hashtag", "").strip().lstrip("#").lower()
    max_count = min(args.get("max_count", 5), 20)
    if not hashtag:
        return "Error: 'hashtag' is required."
    try:
        result = ig.growth.follow_hashtag_users(hashtag, max_count=max_count)
        if isinstance(result, dict):
            followed = result.get("followed", 0)
            return f"✅ Followed {followed} users from #{hashtag}!"
        return f"✅ Follow hashtag users completed! Result: {str(result)[:200]}"
    except Exception as e:
        return f"Error following hashtag users: {e}"
