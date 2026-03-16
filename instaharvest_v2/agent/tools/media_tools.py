"""
Media & Social Tools
====================
Media interaction handlers: download, like, comment, media info,
follow/unfollow, followers/following lists, friendship status.
"""

import json
import os
import re
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _resolve_media_id(media_id_or_url: str, ig) -> str:
    """Resolve Instagram URL to media PK if needed."""
    if media_id_or_url.startswith("http"):
        shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", media_id_or_url)
        if shortcode_match and hasattr(ig, "media"):
            shortcode = shortcode_match.group(1)
            try:
                info = ig.media.get_by_shortcode(shortcode) if hasattr(ig.media, "get_by_shortcode") else None
                if info:
                    return str(info.get("pk", info.get("id", shortcode)))
            except Exception:
                pass
            # Fallback: use shortcode_to_media_id
            if hasattr(ig.media, "_shortcode_to_media_id"):
                return str(ig.media._shortcode_to_media_id(shortcode))
        return media_id_or_url
    return media_id_or_url


# ═══════════════════════════════════════════════════════════
# TOOL 6: download_media
# ═══════════════════════════════════════════════════════════

def handle_download_media(args: Dict, ig=None) -> str:
    """Download Instagram media using instaharvest_v2."""
    url = args.get("url", "")
    output_dir = args.get("output_dir", "downloads")
    media_type = args.get("media_type", "post")

    if not url:
        return "Error: no URL or username provided"

    if ig is None:
        return "Error: Instagram client required. Cannot download in anonymous mode."

    # Security: relative paths only
    if os.path.isabs(output_dir) or ".." in output_dir:
        return "Error: only relative output directories allowed"

    os.makedirs(output_dir, exist_ok=True)
    full_output_path = os.path.abspath(output_dir)

    try:
        # ─── URL-based download ───
        if url.startswith("http"):
            if hasattr(ig, "download") and hasattr(ig.download, "download_by_url"):
                try:
                    files = ig.download.download_by_url(url, folder=output_dir)
                    if files:
                        return (
                            f"✅ Downloaded {len(files)} file(s)\n"
                            f"Path: {full_output_path}\n"
                            f"Files: {', '.join(os.path.basename(f) for f in files)}"
                        )
                except Exception as e:
                    logger.warning(f"download_by_url failed: {e}")

            # Fallback: extract shortcode manually
            shortcode_match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
            if shortcode_match and hasattr(ig, "download"):
                shortcode = shortcode_match.group(1)
                try:
                    media_info = ig.media.get_by_shortcode(shortcode)
                    media_pk = media_info.get("pk") if isinstance(media_info, dict) else getattr(media_info, "pk", None)
                    if media_pk:
                        files = ig.download.download_media(media_pk, folder=output_dir)
                        return (
                            f"✅ Downloaded media (shortcode: {shortcode})\n"
                            f"Path: {full_output_path}\n"
                            f"Files: {len(files) if isinstance(files, list) else 1}"
                        )
                except Exception as e:
                    return f"Error downloading from URL: {e}"

            return f"Error: could not extract media from URL: {url}"

        # ─── Username-based download ───
        username = url.lstrip("@")

        if media_type == "profile_pic":
            if hasattr(ig, "download") and hasattr(ig.download, "download_profile_pic"):
                filepath = ig.download.download_profile_pic(
                    username=username, folder=output_dir
                )
                return (
                    f"✅ Profile pic of @{username} downloaded\n"
                    f"Path: {os.path.abspath(filepath)}"
                )
            return "Error: download_profile_pic not available"

        elif media_type == "stories":
            if hasattr(ig, "download") and hasattr(ig.download, "download_stories"):
                # Need user_pk for stories
                user_data = ig.users.get_by_username(username)
                user_pk = user_data.get("pk") if isinstance(user_data, dict) else getattr(user_data, "pk", None)
                if user_pk:
                    files = ig.download.download_stories(user_pk, folder=output_dir)
                    return (
                        f"✅ Stories of @{username} downloaded\n"
                        f"Path: {full_output_path}\n"
                        f"Files: {len(files) if isinstance(files, list) else '?'}"
                    )
            return "Error: stories download not available"

        elif media_type == "reels" or media_type == "all":
            if hasattr(ig, "bulk_download") and hasattr(ig.bulk_download, "everything"):
                result = ig.bulk_download.everything(username, output_dir)
                return (
                    f"✅ All media of @{username} downloaded\n"
                    f"Path: {full_output_path}\n"
                    f"Result: {json.dumps(result, default=str)[:300]}"
                )
            return "Error: bulk_download not available"

        else:
            # Default: download posts using bulk_download (accepts username)
            if hasattr(ig, "bulk_download") and hasattr(ig.bulk_download, "all_posts"):
                max_count = 10
                result = ig.bulk_download.all_posts(
                    username, output_dir, max_count=max_count
                )
                return (
                    f"✅ Posts of @{username} downloaded\n"
                    f"Path: {full_output_path}\n"
                    f"Result: {json.dumps(result, default=str)[:300]}"
                )

            # Fallback: download_user_posts (needs user_pk)
            if hasattr(ig, "download") and hasattr(ig.download, "download_user_posts"):
                user_data = ig.users.get_by_username(username)
                user_pk = user_data.get("pk") if isinstance(user_data, dict) else getattr(user_data, "pk", None)
                if user_pk:
                    files = ig.download.download_user_posts(
                        user_pk, folder=output_dir, max_posts=10
                    )
                    return (
                        f"✅ {len(files)} posts of @{username} downloaded\n"
                        f"Path: {full_output_path}\n"
                        f"Files: {', '.join(os.path.basename(f) for f in files[:5])}"
                    )
            return "Error: post download not available"

    except Exception as e:
        return f"Error downloading media: {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 15: follow_user
# ═══════════════════════════════════════════════════════════

def handle_follow_user(args: Dict, ig=None, is_logged_in=False) -> str:
    """Follow or unfollow a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    action = args.get("action", "follow").lower()

    if not username:
        return "Error: username is required."
    if not is_logged_in:
        return "Error: follow/unfollow requires login. You are in anonymous mode."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        # Get user PK first
        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        if action == "follow":
            ig.friendships.follow(user_pk)
            return f"✅ Successfully followed @{username}"
        elif action == "unfollow":
            ig.friendships.unfollow(user_pk)
            return f"✅ Successfully unfollowed @{username}"
        else:
            return f"Error: unknown action '{action}'. Use 'follow' or 'unfollow'."

    except Exception as e:
        return f"Error {action}ing @{username}: {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 16: get_followers
# ═══════════════════════════════════════════════════════════

def handle_get_followers(args: Dict, ig=None, is_logged_in=False) -> str:
    """Get followers list for a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    max_count = min(args.get("max_count", 50), 1000)

    if not username:
        return "Error: username is required."
    if not is_logged_in:
        return "Error: followers list requires login. You are in anonymous mode."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        followers = ig.friendships.get_all_followers(user_pk, max_count=max_count)
        if not followers:
            return f"No followers found for '@{username}' (may be private)."

        lines = [f"Followers of @{username} ({len(followers)} shown):"]
        lines.append("-" * 50)

        for i, f in enumerate(followers[:max_count], 1):
            if isinstance(f, dict):
                fname = f.get("full_name", "")
                uname = f.get("username", "?")
                verified = " ✅" if f.get("is_verified") else ""
                lines.append(f"  {i}. @{uname}{verified}" + (f" ({fname})" if fname else ""))
            else:
                uname = getattr(f, "username", str(f))
                lines.append(f"  {i}. @{uname}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting followers for '@{username}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 17: get_following
# ═══════════════════════════════════════════════════════════

def handle_get_following(args: Dict, ig=None, is_logged_in=False) -> str:
    """Get following list for a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    max_count = min(args.get("max_count", 50), 1000)

    if not username:
        return "Error: username is required."
    if not is_logged_in:
        return "Error: following list requires login. You are in anonymous mode."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        following = ig.friendships.get_all_following(user_pk, max_count=max_count)
        if not following:
            return f"No following found for '@{username}' (may be private)."

        lines = [f"Following of @{username} ({len(following)} shown):"]
        lines.append("-" * 50)

        for i, f in enumerate(following[:max_count], 1):
            if isinstance(f, dict):
                fname = f.get("full_name", "")
                uname = f.get("username", "?")
                verified = " ✅" if f.get("is_verified") else ""
                lines.append(f"  {i}. @{uname}{verified}" + (f" ({fname})" if fname else ""))
            else:
                uname = getattr(f, "username", str(f))
                lines.append(f"  {i}. @{uname}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting following for '@{username}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 18: get_friendship_status
# ═══════════════════════════════════════════════════════════

def handle_get_friendship_status(args: Dict, ig=None, is_logged_in=False) -> str:
    """Check friendship status between me and another user."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required."
    if not is_logged_in:
        return "Error: friendship status requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        status = ig.friendships.show(user_pk)
        if not status:
            return f"Could not get friendship status for '@{username}'."

        if isinstance(status, dict):
            lines = [
                f"Friendship status with @{username}:",
                f"  I follow them: {'Yes' if status.get('following') else 'No'}",
                f"  They follow me: {'Yes' if status.get('followed_by') else 'No'}",
                f"  Blocked: {'Yes' if status.get('blocking') else 'No'}",
                f"  Muted: {'Yes' if status.get('muting') else 'No'}",
                f"  Restricted: {'Yes' if status.get('is_restricted') else 'No'}",
            ]
            if status.get("outgoing_request"):
                lines.append("  Pending follow request: Yes")
            return "\n".join(lines)

        return f"Friendship with @{username}: {status}"

    except Exception as e:
        return f"Error checking friendship with '@{username}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 19: like_media
# ═══════════════════════════════════════════════════════════

def handle_like_media(args: Dict, ig=None, is_logged_in=False) -> str:
    """Like or unlike a post."""
    media_id = args.get("media_id", "").strip()
    action = args.get("action", "like").lower()

    if not media_id:
        return "Error: media_id or URL is required."
    if not is_logged_in:
        return "Error: like/unlike requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        resolved_id = _resolve_media_id(media_id, ig)

        if action == "like":
            ig.media.like(resolved_id)
            return f"✅ Liked post (ID: {resolved_id})"
        elif action == "unlike":
            ig.media.unlike(resolved_id)
            return f"✅ Unliked post (ID: {resolved_id})"
        else:
            return f"Error: unknown action '{action}'. Use 'like' or 'unlike'."

    except Exception as e:
        return f"Error {action}ing post: {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 20: comment_media
# ═══════════════════════════════════════════════════════════

def handle_comment_media(args: Dict, ig=None, is_logged_in=False) -> str:
    """Add comment to a post."""
    media_id = args.get("media_id", "").strip()
    text = args.get("text", "").strip()

    if not media_id:
        return "Error: media_id or URL is required."
    if not text:
        return "Error: comment text is required."
    if not is_logged_in:
        return "Error: commenting requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        resolved_id = _resolve_media_id(media_id, ig)
        result = ig.media.comment(resolved_id, text)
        return f"✅ Comment posted: '{text}' (on post {resolved_id})"
    except Exception as e:
        return f"Error commenting: {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 21: get_media_info
# ═══════════════════════════════════════════════════════════

def handle_get_media_info(args: Dict, ig=None) -> str:
    """Get full information about a post."""
    media_id = args.get("media_id", "").strip()

    if not media_id:
        return "Error: media_id or URL is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        # Try URL-based lookup first
        if media_id.startswith("http"):
            if hasattr(ig, "media") and hasattr(ig.media, "get_by_url_v2"):
                info = ig.media.get_by_url_v2(media_id)
            elif hasattr(ig, "public") and hasattr(ig.public, "get_post_by_url"):
                info = ig.public.get_post_by_url(media_id)
            else:
                resolved_id = _resolve_media_id(media_id, ig)
                info = ig.media.get_full_info(resolved_id) if hasattr(ig.media, "get_full_info") else ig.media.get_info(resolved_id)
        else:
            if hasattr(ig, "media") and hasattr(ig.media, "get_full_info"):
                info = ig.media.get_full_info(media_id)
            elif hasattr(ig, "media") and hasattr(ig.media, "get_info"):
                info = ig.media.get_info(media_id)
            else:
                return "Error: media info endpoint not available."

        if not info:
            return f"Post not found: {media_id}"

        if isinstance(info, dict):
            lines = [
                f"Post Info:",
                f"  Type: {info.get('media_type', info.get('type', 'unknown'))}",
                f"  Owner: @{info.get('owner', {}).get('username', info.get('username', 'N/A'))}",
                f"  Likes: {info.get('likes', info.get('like_count', 0)):,}",
                f"  Comments: {info.get('comments_count', info.get('comment_count', 0)):,}",
            ]
            caption = info.get("caption", "")
            if isinstance(caption, dict):
                caption = caption.get("text", "")
            if caption:
                lines.append(f"  Caption: {str(caption)[:200]}")

            shortcode = info.get("code", info.get("shortcode", ""))
            if shortcode:
                lines.append(f"  URL: https://instagram.com/p/{shortcode}/")

            views = info.get("views", info.get("play_count", 0))
            if views:
                lines.append(f"  Views: {views:,}")

            return "\n".join(lines)

        return f"Post info: {str(info)[:500]}"

    except Exception as e:
        return f"Error getting post info: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: ADVANCED MEDIA TOOLS (6 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_likers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get users who liked a post."""
    if not is_logged_in:
        return "❌ Login required to view likers."
    media_id = args.get("media_id", "")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        likers = ig.media.get_likers(media_id)
        if not likers:
            return "No likers found."
        items = likers if isinstance(likers, list) else [likers]
        lines = [f"❤️ Likers ({len(items)} users):"]
        for i, u in enumerate(items[:30], 1):
            if isinstance(u, dict):
                uname = u.get("username", "?")
                fname = u.get("full_name", "")
                lines.append(f"  {i}. @{uname} — {fname}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting likers: {e}"


def handle_save_media(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Save/bookmark a post."""
    if not is_logged_in:
        return "❌ Login required to save media."
    media_id = args.get("media_id", "")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        ig.media.save(media_id)
        return f"✅ Media {media_id} saved (bookmarked) successfully!"
    except Exception as e:
        return f"Error saving media: {e}"


def handle_unsave_media(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Remove media from saved/bookmarks."""
    if not is_logged_in:
        return "❌ Login required to unsave media."
    media_id = args.get("media_id", "")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        ig.media.unsave(media_id)
        return f"✅ Media {media_id} removed from saved!"
    except Exception as e:
        return f"Error unsaving media: {e}"


def handle_get_comment_replies(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get replies to a specific comment."""
    if not is_logged_in:
        return "❌ Login required to view comment replies."
    comment_id = args.get("comment_id", "")
    media_id = args.get("media_id", "")
    if not comment_id or not media_id:
        return "Error: both 'media_id' and 'comment_id' are required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        replies = ig.media.get_comment_replies(media_id, comment_id)
        if not replies:
            return "No replies found."
        items = replies if isinstance(replies, list) else [replies]
        lines = [f"💬 Comment replies ({len(items)}):"]
        for i, r in enumerate(items[:15], 1):
            if isinstance(r, dict):
                user = r.get("user", {}).get("username", "?") if isinstance(r.get("user"), dict) else "?"
                text = str(r.get("text", ""))[:80]
                lines.append(f"  {i}. @{user}: {text}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting comment replies: {e}"


def handle_reply_to_comment(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Reply to a comment on a post."""
    if not is_logged_in:
        return "❌ Login required to reply to comments."
    media_id = args.get("media_id", "")
    comment_id = args.get("comment_id", "")
    text = args.get("text", "")
    if not all([media_id, comment_id, text]):
        return "Error: 'media_id', 'comment_id', and 'text' are all required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        ig.media.reply_to_comment(media_id, comment_id, text)
        return f"✅ Reply posted to comment {comment_id}!"
    except Exception as e:
        return f"Error replying to comment: {e}"


def handle_edit_caption(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Edit the caption of a post."""
    if not is_logged_in:
        return "❌ Login required to edit captions."
    media_id = args.get("media_id", "")
    caption = args.get("caption", "")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        media_id = _resolve_media_id(media_id, ig)
        ig.media.edit_caption(media_id, caption)
        return f"✅ Caption updated for media {media_id}!"
    except Exception as e:
        return f"Error editing caption: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: ADVANCED FRIENDSHIPS (8 tools)
# ═══════════════════════════════════════════════════════════

def handle_block_user(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Block a user."""
    if not is_logged_in:
        return "❌ Login required to block users."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.block(user_id)
        return f"✅ @{username} blocked successfully!"
    except Exception as e:
        return f"Error blocking user: {e}"


def handle_unblock_user(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Unblock a user."""
    if not is_logged_in:
        return "❌ Login required to unblock users."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.unblock(user_id)
        return f"✅ @{username} unblocked!"
    except Exception as e:
        return f"Error unblocking user: {e}"


def handle_mute_user(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Mute a user (posts, stories, or both)."""
    if not is_logged_in:
        return "❌ Login required to mute users."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.mute(user_id)
        return f"✅ @{username} muted!"
    except Exception as e:
        return f"Error muting user: {e}"


def handle_unmute_user(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Unmute a user."""
    if not is_logged_in:
        return "❌ Login required to unmute users."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.unmute(user_id)
        return f"✅ @{username} unmuted!"
    except Exception as e:
        return f"Error unmuting user: {e}"


def handle_remove_follower(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Remove a follower from your account."""
    if not is_logged_in:
        return "❌ Login required to remove followers."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.remove_follower(user_id)
        return f"✅ @{username} removed from followers!"
    except Exception as e:
        return f"Error removing follower: {e}"


def handle_get_pending_requests(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get pending follow requests."""
    if not is_logged_in:
        return "❌ Login required to view pending requests."
    try:
        requests = ig.friendships.get_pending_requests()
        if not requests:
            return "No pending follow requests."
        items = requests if isinstance(requests, list) else [requests]
        lines = [f"📩 Pending Requests ({len(items)}):"]
        for i, u in enumerate(items[:20], 1):
            if isinstance(u, dict):
                uname = u.get("username", "?")
                fname = u.get("full_name", "")
                lines.append(f"  {i}. @{uname} — {fname}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting pending requests: {e}"


def handle_approve_request(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Approve a pending follow request."""
    if not is_logged_in:
        return "❌ Login required to approve requests."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        ig.friendships.approve_request(user_id)
        return f"✅ Follow request from @{username} approved!"
    except Exception as e:
        return f"Error approving request: {e}"


def handle_get_mutual_followers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get mutual followers between you and another user."""
    if not is_logged_in:
        return "❌ Login required to view mutual followers."
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    try:
        user_id = ig.public.get_user_id(username)
        mutuals = ig.friendships.get_mutual_followers(user_id)
        if not mutuals:
            return f"No mutual followers with @{username}."
        items = mutuals if isinstance(mutuals, list) else [mutuals]
        lines = [f"🤝 Mutual followers with @{username} ({len(items)}):"]
        for i, u in enumerate(items[:20], 1):
            if isinstance(u, dict):
                uname = u.get("username", "?")
                lines.append(f"  {i}. @{uname}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting mutual followers: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: STORIES MANAGEMENT (4 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_story_viewers(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get viewers of your story."""
    if not is_logged_in:
        return "❌ Login required to view story viewers."
    story_id = args.get("story_id", "")
    if not story_id:
        return "Error: 'story_id' is required."
    try:
        viewers = ig.stories.get_viewers(story_id)
        if not viewers:
            return "No viewers found."
        items = viewers if isinstance(viewers, list) else [viewers]
        lines = [f"👁 Story viewers ({len(items)}):"]
        for i, v in enumerate(items[:30], 1):
            if isinstance(v, dict):
                uname = v.get("username", "?")
                lines.append(f"  {i}. @{uname}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting story viewers: {e}"


def handle_react_to_story(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """React to a story with an emoji."""
    if not is_logged_in:
        return "❌ Login required to react to stories."
    story_id = args.get("story_id", "")
    emoji = args.get("emoji", "❤️")
    if not story_id:
        return "Error: 'story_id' is required."
    try:
        ig.stories.react_to_story(story_id, emoji)
        return f"✅ Reacted to story with {emoji}!"
    except Exception as e:
        return f"Error reacting to story: {e}"


def handle_create_highlight(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Create a story highlight."""
    if not is_logged_in:
        return "❌ Login required to create highlights."
    title = args.get("title", "")
    story_ids = args.get("story_ids", [])
    if not title or not story_ids:
        return "Error: 'title' and 'story_ids' array are required."
    try:
        ig.stories.create_highlight(title, story_ids)
        return f"✅ Highlight '{title}' created with {len(story_ids)} stories!"
    except Exception as e:
        return f"Error creating highlight: {e}"


def handle_get_all_highlights(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get all highlights with full items for a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        highlights = ig.stories.get_all_highlights_with_items(username)
        if not highlights:
            return f"No highlights found for @{username}."
        items = highlights if isinstance(highlights, list) else [highlights]
        lines = [f"⭐ Highlights for @{username} ({len(items)}):"]
        for i, h in enumerate(items[:15], 1):
            if isinstance(h, dict):
                title = h.get("title", "Untitled")
                count = len(h.get("items", []))
                lines.append(f"  {i}. {title} ({count} items)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting highlights: {e}"

