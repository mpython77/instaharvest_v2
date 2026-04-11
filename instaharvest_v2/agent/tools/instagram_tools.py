"""
Instagram Profile Tools
=======================
Profile, posts, search, user info, stories, hashtag, my account handlers.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# TOOL 11: get_profile
# ═══════════════════════════════════════════════════════════

def handle_get_profile(args: Dict, ig=None, cache=None) -> str:
    """Get Instagram profile info — direct API call, no code needed."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required. Example: get_profile(username='cristiano')"

    if ig is None:
        return "Error: Instagram client not available."

    # Check cache first
    if cache and username in cache:
        cached = cache[username]
        if isinstance(cached, dict):
            return _format_profile(cached, username, from_cache=True)

    try:
        profile = ig.public.get_profile(username)
        if not profile:
            return f"Profile not found: '@{username}'. Check the username spelling."

        # Cache for future use
        if cache is not None:
            cache[username] = profile

        return _format_profile(profile, username)

    except Exception as e:
        return f"Error fetching profile '@{username}': {e}"


def _format_profile(profile: Dict, username: str, from_cache: bool = False) -> str:
    """Format profile data into comprehensive output string."""
    prefix = "(From cache) " if from_cache else ""
    lines = [
        f"{prefix}Profile: @{profile.get('username', username)}",
        f"Full Name: {profile.get('full_name', 'N/A')}",
        f"Followers: {profile.get('followers', 0):,}",
        f"Following: {profile.get('following', 0):,}",
        f"Posts: {profile.get('posts_count', 0):,}",
        f"Bio: {profile.get('biography', 'N/A')}",
        f"Verified: {'Yes ✅' if profile.get('is_verified') else 'No'}",
        f"Private: {'Yes 🔒' if profile.get('is_private') else 'No'}",
    ]

    # User ID
    uid = profile.get("user_id") or profile.get("id")
    if uid:
        lines.append(f"User ID: {uid}")

    # Business/Creator
    if profile.get("is_business"):
        lines.append("Account Type: Business/Creator")
    category = profile.get("category") or profile.get("category_name")
    if category:
        lines.append(f"Category: {category}")

    # Profile picture
    pic = profile.get("profile_pic_url_hd") or profile.get("profile_pic_url")
    if pic:
        lines.append(f"Profile Pic HD: {pic}")

    # Website
    ext_url = profile.get("external_url")
    if ext_url:
        lines.append(f"Website: {ext_url}")

    # Bio links
    bio_links = profile.get("bio_links", [])
    if bio_links and isinstance(bio_links, list):
        for link in bio_links[:5]:
            if isinstance(link, dict):
                title = link.get("title", "")
                url = link.get("url", link.get("lynx_url", ""))
                if url:
                    lines.append(f"Bio Link: {title + ' → ' if title else ''}{url}")

    # Highlights
    hl = profile.get("highlight_count", 0)
    if hl:
        lines.append(f"Highlights: {hl}")

    # Pronouns
    pronouns = profile.get("pronouns", [])
    if pronouns:
        lines.append(f"Pronouns: {'/'.join(pronouns)}")

    # Mutual followers
    mutual = profile.get("mutual_followers", 0)
    if mutual:
        lines.append(f"Mutual Followers: {mutual:,}")

    # Business contact info
    biz_email = profile.get("business_email")
    if biz_email:
        lines.append(f"Business Email: {biz_email}")
    biz_phone = profile.get("business_phone")
    if biz_phone:
        lines.append(f"Business Phone: {biz_phone}")

    # Recent posts summary
    recent = profile.get("recent_posts", [])
    if recent:
        lines.append(f"\nRecent Posts ({len(recent)}):")
        for i, post in enumerate(recent[:5], 1):
            if isinstance(post, dict):
                caption = str(post.get("caption", ""))[:60]
                likes = post.get("likes", post.get("like_count", 0))
                comments = post.get("comments", post.get("comment_count", 0))
                lines.append(f"  {i}. {caption}{'...' if len(str(post.get('caption', ''))) > 60 else ''}")
                lines.append(f"     ❤️ {likes:,}  💬 {comments:,}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# TOOL 12: get_posts
# ═══════════════════════════════════════════════════════════

def handle_get_posts(args: Dict, ig=None, cache=None) -> str:
    """Get user's recent Instagram posts — direct API call."""
    username = args.get("username", "").strip().lstrip("@").lower()
    max_count = min(args.get("max_count", 12), 50)

    if not username:
        return "Error: username is required."

    if ig is None:
        return "Error: Instagram client not available."

    try:
        posts = ig.public.get_posts(username)
        if not posts:
            return f"No posts found for '@{username}' or profile is private."

        # Limit to max_count
        posts = posts[:max_count] if isinstance(posts, list) else [posts]

        lines = [f"Recent posts from @{username} ({len(posts)} posts):"]
        lines.append("-" * 50)

        for i, post in enumerate(posts, 1):
            if isinstance(post, dict):
                shortcode = post.get("shortcode", "?")
                likes = post.get("like_count", post.get("likes", 0))
                comments = post.get("comment_count", post.get("comments", 0))
                caption = post.get("caption", "") or ""
                timestamp = post.get("taken_at", post.get("timestamp", ""))
                media_type = post.get("media_type", post.get("type", "photo"))

                # Truncate caption
                if len(caption) > 100:
                    caption = caption[:100] + "..."

                lines.append(f"\n  {i}. [{media_type}] https://instagram.com/p/{shortcode}/")
                if likes:
                    lines.append(f"     Likes: {likes:,}")
                if comments:
                    lines.append(f"     Comments: {comments:,}")
                if caption:
                    lines.append(f"     Caption: {caption}")
                if timestamp:
                    lines.append(f"     Date: {timestamp}")
            else:
                lines.append(f"\n  {i}. {str(post)[:200]}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching posts for '@{username}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 13: search_users
# ═══════════════════════════════════════════════════════════

def handle_search_users(args: Dict, ig=None, **kw) -> str:
    """Search Instagram for users — direct API call."""
    query = args.get("query", "").strip()

    if not query:
        return "Error: search query is required."

    if ig is None:
        return "Error: Instagram client not available."

    try:
        # Try public search first
        if hasattr(ig, "public") and hasattr(ig.public, "search"):
            results = ig.public.search(query)
        elif hasattr(ig, "users") and hasattr(ig.users, "search"):
            results = ig.users.search(query)
        else:
            return "Error: search is not available in current mode."

        if not results:
            return f"No users found for query: '{query}'"

        items = results if isinstance(results, list) else [results]
        lines = [f"Search results for '{query}' ({len(items)} found):"]
        lines.append("-" * 50)

        for i, user in enumerate(items[:10], 1):
            if isinstance(user, dict):
                uname = user.get("username", "?")
                fname = user.get("full_name", "")
                followers = user.get("followers", user.get("follower_count", "?"))
                verified = " ✅" if user.get("is_verified") else ""
                private = " 🔒" if user.get("is_private") else ""

                lines.append(f"\n  {i}. @{uname}{verified}{private}")
                if fname:
                    lines.append(f"     Name: {fname}")
                if isinstance(followers, int):
                    lines.append(f"     Followers: {followers:,}")
            else:
                lines.append(f"\n  {i}. {str(user)[:200]}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error searching for '{query}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 14: get_user_info
# ═══════════════════════════════════════════════════════════

def handle_get_user_info(args: Dict, ig=None, is_logged_in=False, cache=None) -> str:
    """Get detailed user info — uses login API if available, fallback to public."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required."

    if ig is None:
        return "Error: Instagram client not available."

    # Try login API first (more detailed data)
    if is_logged_in and hasattr(ig, "users") and hasattr(ig.users, "get_by_username"):
        try:
            user = ig.users.get_by_username(username)
            if user:
                # Handle both dict and object responses
                if isinstance(user, dict):
                    data = user
                else:
                    data = {
                        "username": getattr(user, "username", username),
                        "full_name": getattr(user, "full_name", "N/A"),
                        "followers": getattr(user, "followers", 0),
                        "following": getattr(user, "following", 0),
                        "posts_count": getattr(user, "posts_count", 0),
                        "biography": getattr(user, "biography", ""),
                        "is_verified": getattr(user, "is_verified", False),
                        "is_private": getattr(user, "is_private", False),
                        "is_business": getattr(user, "is_business_account", False),
                        "category": getattr(user, "category_name", ""),
                        "external_url": getattr(user, "external_url", ""),
                        "profile_pic_url": getattr(user, "profile_pic_url", ""),
                    }

                lines = [
                    f"Detailed Profile: @{data.get('username', username)}",
                    f"Full Name: {data.get('full_name', 'N/A')}",
                    f"Followers: {data.get('followers', 0):,}",
                    f"Following: {data.get('following', 0):,}",
                    f"Posts: {data.get('posts_count', 0):,}",
                    f"Bio: {data.get('biography', 'N/A')}",
                    f"Verified: {'Yes' if data.get('is_verified') else 'No'}",
                    f"Private: {'Yes' if data.get('is_private') else 'No'}",
                    f"Business: {'Yes' if data.get('is_business') else 'No'}",
                ]

                if data.get("category"):
                    lines.append(f"Category: {data['category']}")
                if data.get("external_url"):
                    lines.append(f"Website: {data['external_url']}")
                if data.get("profile_pic_url"):
                    lines.append(f"Profile Pic: {data['profile_pic_url']}")

                # Cache
                if cache is not None:
                    cache[username] = data

                return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Login API failed for '{username}': {e}, falling back to public")

    # Fallback to public API
    return handle_get_profile(args, ig=ig, cache=cache)


# ═══════════════════════════════════════════════════════════
# TOOL 22: get_stories
# ═══════════════════════════════════════════════════════════

def handle_get_stories(args: Dict, ig=None, is_logged_in=False) -> str:
    """Get user's stories."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required."
    if not is_logged_in:
        return "Error: viewing stories requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        # Try parsed stories first
        if hasattr(ig, "stories") and hasattr(ig.stories, "get_stories_parsed"):
            stories = ig.stories.get_stories_parsed(user_pk)
        elif hasattr(ig, "stories") and hasattr(ig.stories, "get_user_stories"):
            stories = ig.stories.get_user_stories(user_pk)
        else:
            return "Error: stories API not available."

        if not stories:
            return f"No active stories for @{username}."

        # Parse response
        items = []
        if isinstance(stories, dict):
            items = stories.get("items", stories.get("reel", {}).get("items", []))
        elif isinstance(stories, list):
            items = stories

        if not items:
            return f"No active stories for @{username}."

        lines = [f"Stories from @{username} ({len(items)} items):"]
        lines.append("-" * 50)

        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                mtype = "Photo" if item.get("media_type", 1) == 1 else "Video"
                timestamp = item.get("taken_at", item.get("timestamp", ""))
                lines.append(f"\n  {i}. [{mtype}] - {timestamp}")

                # Media URL
                if mtype == "Video":
                    videos = item.get("video_versions", [])
                    if videos:
                        lines.append(f"     URL: {videos[0].get('url', 'N/A')[:100]}")
                else:
                    images = item.get("image_versions2", {}).get("candidates", [])
                    if images:
                        lines.append(f"     URL: {images[0].get('url', 'N/A')[:100]}")

                viewers = item.get("viewer_count", item.get("total_viewer_count"))
                if viewers:
                    lines.append(f"     Viewers: {viewers:,}")
            else:
                lines.append(f"\n  {i}. {str(item)[:200]}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting stories for '@{username}': {e}"


# ═══════════════════════════════════════════════════════════
# TOOL 24: get_hashtag_info (fixed — works without login!)
# ═══════════════════════════════════════════════════════════

def handle_get_hashtag_info(args: Dict, ig=None, is_logged_in=False) -> str:
    """Get hashtag information — works in anonymous mode too."""
    hashtag = args.get("hashtag", "").strip().lstrip("#").lower()

    if not hashtag:
        return "Error: hashtag name is required."
    if ig is None:
        return "Error: Instagram client not available."

    # Try public API first (no login needed!)
    if hasattr(ig, "public") and hasattr(ig.public, "get_hashtag_posts_v2"):
        try:
            result = ig.public.get_hashtag_posts_v2(hashtag, max_count=5)
            if result and isinstance(result, dict):
                lines = [
                    f"Hashtag Info: #{hashtag}",
                    f"  Media Count: {result.get('media_count', 'N/A'):,}" if isinstance(result.get('media_count'), int) else f"  Media Count: {result.get('media_count', 'N/A')}",
                    f"  More Available: {'Yes' if result.get('more_available') else 'No'}",
                ]
                posts = result.get("posts", [])
                if posts:
                    lines.append(f"  Posts Fetched: {len(posts)}")
                    for i, p in enumerate(posts[:3], 1):
                        if isinstance(p, dict):
                            likes = p.get("like_count", p.get("likes", 0))
                            caption = str(p.get("caption", ""))[:60]
                            lines.append(f"    {i}. ❤️ {likes:,} — {caption}{'...' if len(str(p.get('caption', ''))) > 60 else ''}")
                return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Public hashtag API failed: {e}")

    # Fallback: login API
    if is_logged_in and hasattr(ig, "hashtags") and hasattr(ig.hashtags, "get_info"):
        try:
            info = ig.hashtags.get_info(hashtag)
            if info and isinstance(info, dict):
                lines = [
                    f"Hashtag Info: #{hashtag}",
                    f"  Posts: {info.get('media_count', 0):,}",
                ]
                if info.get("name"):
                    lines.append(f"  Name: {info['name']}")
                if info.get("id"):
                    lines.append(f"  ID: {info['id']}")
                return "\n".join(lines)
            return f"Hashtag #{hashtag}: {str(info)[:500]}"
        except Exception as e:
            return f"Error getting hashtag info: {e}"

    return f"Error: hashtag info not available for '#{hashtag}'."


# ═══════════════════════════════════════════════════════════
# TOOL 25: get_my_account
# ═══════════════════════════════════════════════════════════

def handle_get_my_account(args: Dict, ig=None, is_logged_in=False) -> str:
    """Get current logged-in user info."""
    if not is_logged_in:
        return "Error: account info requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        if hasattr(ig, "account") and hasattr(ig.account, "get_current_user"):
            user = ig.account.get_current_user()
        else:
            return "Error: account API not available."

        if not user or (isinstance(user, dict) and user.get("status") == "fail"):
            msg = user.get("message", "unknown error") if isinstance(user, dict) else "no data"
            return f"Error: could not get account info: {msg}"

        if isinstance(user, dict):
            lines = [
                f"My Account:",
                f"  Username: @{user.get('username', 'N/A')}",
                f"  Full Name: {user.get('full_name', 'N/A')}",
                f"  Followers: {user.get('followers', user.get('follower_count', 0)):,}",
                f"  Following: {user.get('following', user.get('following_count', 0)):,}",
                f"  Posts: {user.get('posts_count', user.get('media_count', 0)):,}",
                f"  Bio: {user.get('biography', 'N/A')}",
                f"  Verified: {'Yes' if user.get('is_verified') else 'No'}",
                f"  Private: {'Yes' if user.get('is_private') else 'No'}",
            ]
            if user.get("external_url"):
                lines.append(f"  Website: {user['external_url']}")
            if user.get("email"):
                lines.append(f"  Email: {user['email']}")
            return "\n".join(lines)

        return f"My account: {str(user)[:500]}"

    except Exception as e:
        return f"Error getting account info: {e}"


# ═══════════════════════════════════════════════════════════
# NEW PUBLIC ANONYMOUS TOOLS (login talab qilmaydi)
# ═══════════════════════════════════════════════════════════


# ── get_user_id ──
def handle_get_user_id(args: Dict, ig=None, **kw) -> str:
    """Get user ID from username — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        uid = ig.public.get_user_id(username)
        if uid:
            return f"User ID for @{username}: {uid}"
        return f"Could not find user ID for @{username}."
    except Exception as e:
        return f"Error getting user ID: {e}"


# ── is_public ──
def handle_is_public(args: Dict, ig=None, **kw) -> str:
    """Check if account is public — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.public.is_public(username)
        if result is True:
            return f"@{username} is PUBLIC ✅ — content is accessible."
        elif result is False:
            return f"@{username} is PRIVATE 🔒 — content is restricted."
        return f"Could not determine if @{username} is public."
    except Exception as e:
        return f"Error checking account visibility: {e}"


# ── exists ──
def handle_exists(args: Dict, ig=None, **kw) -> str:
    """Check if account exists — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.public.exists(username)
        if result is True:
            return f"@{username} EXISTS ✅"
        elif result is False:
            return f"@{username} does NOT exist ❌"
        return f"Could not determine if @{username} exists."
    except Exception as e:
        return f"Error checking account existence: {e}"


# ── get_feed ──
def handle_get_feed(args: Dict, ig=None, cache=None, **kw) -> str:
    """Get user feed by user_id — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    user_id = args.get("user_id")
    max_count = min(args.get("max_count", 12), 50)

    if not user_id and not username:
        return "Error: user_id or username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        # Resolve user_id from username if needed
        if not user_id and username:
            user_id = ig.public.get_user_id(username)
            if not user_id:
                return f"Could not get user ID for @{username}."

        feed = ig.public.get_feed(user_id, max_count=max_count)
        if not feed:
            return f"No feed data for user_id={user_id}."

        if isinstance(feed, dict):
            items = feed.get("items", [])
            lines = [f"Feed for user_id={user_id} ({len(items)} items):"]
            for i, item in enumerate(items[:10], 1):
                if isinstance(item, dict):
                    sc = item.get("shortcode", item.get("code", ""))
                    likes = item.get("like_count", 0)
                    caption = str(item.get("caption", ""))[:60]
                    lines.append(f"  {i}. https://instagram.com/p/{sc}/ ❤️{likes:,} — {caption}")
            return "\n".join(lines)

        return f"Feed: {str(feed)[:500]}"
    except Exception as e:
        return f"Error getting feed: {e}"


# ── get_tagged_posts ──
def handle_get_tagged_posts(args: Dict, ig=None, **kw) -> str:
    """Get tagged posts for a user — anonymous/public."""
    username = args.get("username", "").strip().lstrip("@").lower()
    user_id = args.get("user_id")
    max_count = min(args.get("max_count", 12), 50)

    if not user_id and not username:
        return "Error: user_id or username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        # Resolve user_id from username if needed
        if not user_id and username:
            user_id = ig.public.get_user_id(username)
            if not user_id:
                return f"Could not get user ID for @{username}."

        posts = ig.graphql.get_tagged_posts(user_id, count=max_count)
        if not posts:
            return f"No tagged posts found for user_id={user_id}."

        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Tagged posts for user_id={user_id} ({len(items)} items):"]
        for i, item in enumerate(items[:12], 1):
            if isinstance(item, dict):
                sc = item.get("shortcode", item.get("code", ""))
                likes = item.get("like_count", item.get("likes", 0))
                owner = item.get("owner", {}).get("username", "?")
                lines.append(f"  {i}. https://instagram.com/p/{sc}/ (by @{owner}) ❤️{likes:,}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting tagged posts: {e}"


# ── get_all_posts ──
def handle_get_all_posts(args: Dict, ig=None, **kw) -> str:
    """Get all posts for a user — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    max_count = min(args.get("max_count", 20), 100)

    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        posts = ig.public.get_all_posts(username, max_count=max_count)
        if not posts:
            return f"No posts found for @{username}."

        items = posts if isinstance(posts, list) else [posts]
        lines = [f"All posts from @{username} ({len(items)} posts):"]
        lines.append("-" * 50)

        for i, post in enumerate(items[:20], 1):
            if isinstance(post, dict):
                sc = post.get("shortcode", post.get("code", ""))
                likes = post.get("like_count", post.get("likes", 0))
                comments = post.get("comment_count", post.get("comments", 0))
                caption = str(post.get("caption", ""))[:60]
                lines.append(f"  {i}. https://instagram.com/p/{sc}/")
                lines.append(f"     ❤️ {likes:,}  💬 {comments:,}  {caption}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting all posts: {e}"


# ── get_reels ──
def handle_get_reels(args: Dict, ig=None, **kw) -> str:
    """Get user's reels — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()
    max_count = min(args.get("max_count", 10), 50)

    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        reels = ig.public.get_reels(username, max_count=max_count)
        if not reels:
            return f"No reels found for @{username}."

        items = reels if isinstance(reels, list) else [reels]
        lines = [f"Reels from @{username} ({len(items)} reels):"]

        for i, reel in enumerate(items[:10], 1):
            if isinstance(reel, dict):
                sc = reel.get("shortcode", reel.get("code", ""))
                views = reel.get("play_count", reel.get("views", 0))
                likes = reel.get("like_count", reel.get("likes", 0))
                lines.append(f"  {i}. https://instagram.com/reel/{sc}/")
                lines.append(f"     👁️ {views:,}  ❤️ {likes:,}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting reels: {e}"


# ── get_comments ──
def handle_get_comments(args: Dict, ig=None, **kw) -> str:
    """Get post comments — anonymous."""
    shortcode = args.get("shortcode", "").strip()
    max_count = min(args.get("max_count", 20), 100)

    if not shortcode:
        return "Error: shortcode is required (e.g. 'CxYzAbCdEf')."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        comments = ig.public.get_comments(shortcode, max_count=max_count)
        if not comments:
            return f"No comments found for post {shortcode}."

        items = comments if isinstance(comments, list) else [comments]
        lines = [f"Comments for post {shortcode} ({len(items)} comments):"]

        for i, c in enumerate(items[:15], 1):
            if isinstance(c, dict):
                user = c.get("owner", {}).get("username", c.get("username", "?"))
                text = str(c.get("text", ""))[:100]
                likes = c.get("likes", c.get("comment_like_count", 0))
                lines.append(f"  {i}. @{user}: {text}")
                if likes:
                    lines.append(f"     ❤️ {likes:,}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting comments: {e}"


# ── get_highlights ──
def handle_get_highlights(args: Dict, ig=None, **kw) -> str:
    """Get user highlights — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        highlights = ig.public.get_highlights(username)
        if not highlights:
            return f"No highlights found for @{username}."

        items = highlights if isinstance(highlights, list) else [highlights]
        lines = [f"Highlights from @{username} ({len(items)} highlights):"]

        for i, hl in enumerate(items[:10], 1):
            if isinstance(hl, dict):
                title = hl.get("title", "Untitled")
                count = hl.get("media_count", hl.get("item_count", "?"))
                lines.append(f"  {i}. \"{title}\" ({count} items)")
            else:
                lines.append(f"  {i}. {str(hl)[:100]}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting highlights: {e}"


# ── get_similar_accounts ──
def handle_get_similar_accounts(args: Dict, ig=None, **kw) -> str:
    """Get similar accounts — anonymous."""
    username = args.get("username", "").strip().lstrip("@").lower()

    if not username:
        return "Error: username is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        similar = ig.public.get_similar_accounts(username)
        if not similar:
            return f"No similar accounts found for @{username}."

        items = similar if isinstance(similar, list) else [similar]
        lines = [f"Similar accounts to @{username} ({len(items)} found):"]

        for i, acc in enumerate(items[:10], 1):
            if isinstance(acc, dict):
                uname = acc.get("username", "?")
                fname = acc.get("full_name", "")
                followers = acc.get("followers", acc.get("follower_count", ""))
                verified = " ✅" if acc.get("is_verified") else ""
                line = f"  {i}. @{uname}{verified}"
                if fname:
                    line += f" ({fname})"
                if isinstance(followers, int):
                    line += f" — {followers:,} followers"
                lines.append(line)

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting similar accounts: {e}"


# ── get_post_by_shortcode ──
def handle_get_post_by_shortcode(args: Dict, ig=None, **kw) -> str:
    """Get post details by shortcode — anonymous."""
    shortcode = args.get("shortcode", "").strip()

    if not shortcode:
        return "Error: shortcode is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        post = ig.public.get_post_by_shortcode(shortcode)
        if not post:
            return f"Post not found: {shortcode}"

        if isinstance(post, dict):
            lines = [
                f"Post: https://instagram.com/p/{post.get('shortcode', shortcode)}/",
                f"  Owner: @{post.get('owner', {}).get('username', post.get('username', 'N/A'))}",
                f"  Type: {post.get('media_type', post.get('type', 'N/A'))}",
                f"  Likes: {post.get('like_count', post.get('likes', 0)):,}",
                f"  Comments: {post.get('comment_count', post.get('comments', 0)):,}",
            ]
            caption = post.get("caption", "")
            if isinstance(caption, dict):
                caption = caption.get("text", "")
            if caption:
                lines.append(f"  Caption: {str(caption)[:200]}")
            views = post.get("play_count", post.get("views", 0))
            if views:
                lines.append(f"  Views: {views:,}")
            return "\n".join(lines)

        return f"Post {shortcode}: {str(post)[:500]}"
    except Exception as e:
        return f"Error getting post: {e}"


# ── get_post_by_url ──
def handle_get_post_by_url(args: Dict, ig=None, **kw) -> str:
    """Get post details by URL — anonymous."""
    url = args.get("url", "").strip()

    if not url:
        return "Error: Instagram post URL is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        post = ig.public.get_post_by_url(url)
        if not post:
            return f"Post not found at URL: {url}"

        if isinstance(post, dict):
            shortcode = post.get("shortcode", post.get("code", "?"))
            lines = [
                f"Post: https://instagram.com/p/{shortcode}/",
                f"  Owner: @{post.get('owner', {}).get('username', post.get('username', 'N/A'))}",
                f"  Type: {post.get('media_type', post.get('type', 'N/A'))}",
                f"  Likes: {post.get('like_count', post.get('likes', 0)):,}",
                f"  Comments: {post.get('comment_count', post.get('comments', 0)):,}",
            ]
            caption = post.get("caption", "")
            if isinstance(caption, dict):
                caption = caption.get("text", "")
            if caption:
                lines.append(f"  Caption: {str(caption)[:200]}")
            return "\n".join(lines)

        return f"Post: {str(post)[:500]}"
    except Exception as e:
        return f"Error getting post from URL: {e}"


# ── get_media_urls ──
def handle_get_media_urls(args: Dict, ig=None, **kw) -> str:
    """Get media download URLs from post — anonymous."""
    shortcode = args.get("shortcode", "").strip()

    if not shortcode:
        return "Error: shortcode is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        urls = ig.public.get_media_urls(shortcode)
        if not urls:
            return f"No media URLs found for {shortcode}."

        if isinstance(urls, list):
            lines = [f"Media URLs for {shortcode} ({len(urls)} files):"]
            for i, url in enumerate(urls[:10], 1):
                if isinstance(url, str):
                    lines.append(f"  {i}. {url[:150]}")
                elif isinstance(url, dict):
                    lines.append(f"  {i}. {url.get('url', str(url))[:150]}")
            return "\n".join(lines)
        elif isinstance(urls, str):
            return f"Media URL: {urls}"

        return f"Media URLs: {str(urls)[:500]}"
    except Exception as e:
        return f"Error getting media URLs: {e}"


# ── get_hashtag_posts ──
def handle_get_hashtag_posts(args: Dict, ig=None, **kw) -> str:
    """Get posts from hashtag — anonymous, no login needed."""
    hashtag = args.get("hashtag", "").strip().lstrip("#").lower()
    max_count = min(args.get("max_count", 10), 50)

    if not hashtag:
        return "Error: hashtag is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        posts = ig.public.get_hashtag_posts(hashtag, max_count=max_count)
        if not posts:
            return f"No posts found for #{hashtag}."

        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Posts for #{hashtag} ({len(items)} posts):"]

        for i, p in enumerate(items[:10], 1):
            if isinstance(p, dict):
                sc = p.get("shortcode", p.get("code", ""))
                likes = p.get("like_count", p.get("likes", 0))
                owner = p.get("owner", {}).get("username", "?") if isinstance(p.get("owner"), dict) else "?"
                lines.append(f"  {i}. @{owner} https://instagram.com/p/{sc}/ ❤️{likes:,}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting hashtag posts: {e}"


# ── get_location_posts ──
def handle_get_location_posts(args: Dict, ig=None, **kw) -> str:
    """Get posts from location — anonymous."""
    location_id = args.get("location_id", "").strip()
    max_count = min(args.get("max_count", 10), 50)

    if not location_id:
        return "Error: location_id is required."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        posts = ig.public.get_location_posts(location_id, max_count=max_count)
        if not posts:
            return f"No posts found for location {location_id}."

        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Posts for location {location_id} ({len(items)} posts):"]

        for i, p in enumerate(items[:10], 1):
            if isinstance(p, dict):
                sc = p.get("shortcode", p.get("code", ""))
                likes = p.get("like_count", p.get("likes", 0))
                owner = p.get("owner", {}).get("username", "?") if isinstance(p.get("owner"), dict) else "?"
                lines.append(f"  {i}. @{owner} https://instagram.com/p/{sc}/ ❤️{likes:,}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting location posts: {e}"


# ── run_diagnostics ──
def handle_run_diagnostics(args: Dict, ig=None, **kw) -> str:
    """Run API diagnostics — anonymous."""
    username = args.get("username", "cristiano").strip().lstrip("@").lower()
    layer = args.get("layer")
    sync_only = args.get("sync_only", True)

    if ig is None:
        return "Error: Instagram client not available."

    try:
        from ..diagnostics import run_diagnostics
        results = run_diagnostics(
            ig,
            username=username,
            sync_only=sync_only,
            layer_filter=layer,
        )
        ok = sum(1 for r in results if r.status == "ok")
        none_c = sum(1 for r in results if r.status == "none")
        err = sum(1 for r in results if r.status == "error")
        total = len(results)
        errors = [r.name for r in results if r.status == "error"]

        lines = [
            f"Diagnostics Result ({total} methods):",
            f"  ✅ OK: {ok}",
            f"  ⚪ None: {none_c}",
            f"  ❌ Errors: {err}",
        ]
        if errors:
            lines.append(f"  Failed: {', '.join(errors)}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error running diagnostics: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: UPLOAD & CONTENT CREATION (7 tools)
# ═══════════════════════════════════════════════════════════

def handle_upload_photo(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a photo post."""
    if not is_logged_in:
        return "❌ Login required to upload photos."
    path = args.get("path", "")
    caption = args.get("caption", "")
    if not path:
        return "Error: 'path' to image file is required."
    try:
        result = ig.upload.post_photo(path, caption=caption)
        if result:
            media_id = result.get("media", {}).get("pk", "") if isinstance(result, dict) else getattr(result, "pk", "")
            return f"✅ Photo uploaded successfully! Media ID: {media_id}"
        return "Photo uploaded but no confirmation received."
    except Exception as e:
        return f"Error uploading photo: {e}"


def handle_upload_video(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a video post."""
    if not is_logged_in:
        return "❌ Login required to upload videos."
    path = args.get("path", "")
    caption = args.get("caption", "")
    if not path:
        return "Error: 'path' to video file is required."
    try:
        result = ig.upload.post_video(path, caption=caption)
        return f"✅ Video uploaded successfully!"
    except Exception as e:
        return f"Error uploading video: {e}"


def handle_upload_reel(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a reel."""
    if not is_logged_in:
        return "❌ Login required to upload reels."
    path = args.get("path", "")
    caption = args.get("caption", "")
    if not path:
        return "Error: 'path' to video file is required."
    try:
        result = ig.upload.post_reel(path, caption=caption)
        return f"✅ Reel uploaded successfully!"
    except Exception as e:
        return f"Error uploading reel: {e}"


def handle_upload_story_photo(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a photo story."""
    if not is_logged_in:
        return "❌ Login required to upload stories."
    path = args.get("path", "")
    if not path:
        return "Error: 'path' to image file is required."
    try:
        result = ig.upload.post_story_photo(path)
        return f"✅ Story photo uploaded successfully!"
    except Exception as e:
        return f"Error uploading story photo: {e}"


def handle_upload_story_video(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a video story."""
    if not is_logged_in:
        return "❌ Login required to upload stories."
    path = args.get("path", "")
    if not path:
        return "Error: 'path' to video file is required."
    try:
        result = ig.upload.post_story_video(path)
        return f"✅ Story video uploaded successfully!"
    except Exception as e:
        return f"Error uploading story video: {e}"


def handle_upload_carousel(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Upload a carousel (multiple photos/videos)."""
    if not is_logged_in:
        return "❌ Login required to upload carousels."
    paths = args.get("paths", [])
    caption = args.get("caption", "")
    if not paths or not isinstance(paths, list):
        return "Error: 'paths' array of media file paths is required."
    try:
        result = ig.upload.post_carousel(paths, caption=caption)
        return f"✅ Carousel uploaded with {len(paths)} items!"
    except Exception as e:
        return f"Error uploading carousel: {e}"


def handle_delete_media(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Delete a media post."""
    if not is_logged_in:
        return "❌ Login required to delete media."
    media_id = args.get("media_id", "")
    if not media_id:
        return "Error: 'media_id' is required."
    try:
        ig.upload.delete_media(media_id)
        return f"✅ Media {media_id} deleted successfully!"
    except Exception as e:
        return f"Error deleting media: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: LOCATION TOOLS (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_search_locations(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Search Instagram locations."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' is required (e.g. 'New York', 'Tashkent')."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        results = ig.location.search(query)
        if not results:
            return f"No locations found for '{query}'."
        items = results if isinstance(results, list) else [results]
        lines = [f"Locations for '{query}' ({len(items)} found):"]
        for i, loc in enumerate(items[:10], 1):
            if isinstance(loc, dict):
                name = loc.get("name", "?")
                loc_id = loc.get("pk", loc.get("location_id", loc.get("id", "?")))
                address = loc.get("address", "")
                lines.append(f"  {i}. {name} (ID: {loc_id}) {address}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching locations: {e}"


def handle_get_location_info(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get location details by ID."""
    location_id = args.get("location_id", "").strip()
    if not location_id:
        return "Error: 'location_id' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        info = ig.location.get_info(location_id)
        if not info:
            return f"Location {location_id} not found."
        if isinstance(info, dict):
            name = info.get("name", "?")
            lat = info.get("lat", "?")
            lng = info.get("lng", "?")
            address = info.get("address", "")
            return (
                f"📍 Location: {name}\n"
                f"  ID: {location_id}\n"
                f"  Address: {address}\n"
                f"  Coordinates: {lat}, {lng}"
            )
        return str(info)[:500]
    except Exception as e:
        return f"Error getting location info: {e}"


def handle_get_nearby_locations(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get nearby locations by coordinates."""
    lat = args.get("lat", args.get("latitude"))
    lng = args.get("lng", args.get("longitude"))
    if not lat or not lng:
        return "Error: 'lat' and 'lng' coordinates are required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        results = ig.location.get_nearby(float(lat), float(lng))
        if not results:
            return f"No nearby locations found at {lat}, {lng}."
        items = results if isinstance(results, list) else [results]
        lines = [f"Nearby locations ({len(items)} found):"]
        for i, loc in enumerate(items[:10], 1):
            if isinstance(loc, dict):
                name = loc.get("name", "?")
                loc_id = loc.get("pk", loc.get("id", "?"))
                lines.append(f"  {i}. {name} (ID: {loc_id})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting nearby locations: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: FEED TOOLS (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_timeline(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get user's home timeline."""
    if not is_logged_in:
        return "❌ Login required to view timeline."
    max_count = min(args.get("max_count", 10), 20)
    try:
        posts = ig.feed.get_timeline(max_count=max_count)
        if not posts:
            return "No timeline posts found."
        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Timeline ({len(items)} posts):"]
        for i, p in enumerate(items[:max_count], 1):
            if isinstance(p, dict):
                user = p.get("user", {}).get("username", "?") if isinstance(p.get("user"), dict) else "?"
                likes = p.get("like_count", 0)
                caption = str(p.get("caption", {}).get("text", ""))[:60] if isinstance(p.get("caption"), dict) else ""
                lines.append(f"  {i}. @{user} ❤️{likes:,} — {caption}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting timeline: {e}"


def handle_get_saved_posts(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get saved/bookmarked posts."""
    if not is_logged_in:
        return "❌ Login required to view saved posts."
    max_count = min(args.get("max_count", 10), 50)
    try:
        posts = ig.feed.get_saved(max_count=max_count)
        if not posts:
            return "No saved posts found."
        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Saved posts ({len(items)} items):"]
        for i, p in enumerate(items[:max_count], 1):
            if isinstance(p, dict):
                sc = p.get("shortcode", p.get("code", "?"))
                likes = p.get("like_count", 0)
                lines.append(f"  {i}. https://instagram.com/p/{sc}/ ❤️{likes:,}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting saved posts: {e}"


def handle_get_liked_posts(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get posts you've liked."""
    if not is_logged_in:
        return "❌ Login required to view liked posts."
    max_count = min(args.get("max_count", 10), 50)
    try:
        posts = ig.feed.get_liked(max_count=max_count)
        if not posts:
            return "No liked posts found."
        items = posts if isinstance(posts, list) else [posts]
        lines = [f"Liked posts ({len(items)} items):"]
        for i, p in enumerate(items[:max_count], 1):
            if isinstance(p, dict):
                sc = p.get("shortcode", p.get("code", "?"))
                user = p.get("user", {}).get("username", "?") if isinstance(p.get("user"), dict) else "?"
                lines.append(f"  {i}. @{user} https://instagram.com/p/{sc}/")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting liked posts: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: USERS TOOLS (2 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_full_profile(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get comprehensive user profile (login required for full data)."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        if is_logged_in:
            profile = ig.users.get_full_profile(username)
        else:
            profile = ig.public.get_profile(username)
        if not profile:
            return f"Profile not found: @{username}"
        if isinstance(profile, dict):
            lines = [f"👤 Full Profile: @{username}"]
            for key in ["username", "full_name", "biography", "followers", "following",
                        "posts_count", "is_verified", "is_private", "is_business",
                        "category", "external_url", "profile_pic_url_hd"]:
                val = profile.get(key)
                if val is not None:
                    if isinstance(val, int) and val > 1000:
                        lines.append(f"  {key}: {val:,}")
                    else:
                        lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(profile)[:800]
    except Exception as e:
        return f"Error getting full profile: {e}"


def handle_parse_bio(args: Dict, ig=None, **kw) -> str:
    """Parse Instagram bio for emails, phones, URLs, hashtags, mentions."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        bio_data = ig.users.parse_bio(username)
        if not bio_data:
            return f"No bio data found for @{username}."
        if isinstance(bio_data, dict):
            lines = [f"📋 Bio Analysis: @{username}"]
            for key, val in bio_data.items():
                if val:
                    lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(bio_data)[:500]
    except Exception as e:
        return f"Error parsing bio: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: HASHTAG RESEARCH (2 tools)
# ═══════════════════════════════════════════════════════════

def handle_analyze_hashtag(args: Dict, ig=None, **kw) -> str:
    """Analyze a hashtag — post count, engagement, competition."""
    hashtag = args.get("hashtag", "").strip().lstrip("#").lower()
    if not hashtag:
        return "Error: 'hashtag' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.hashtag_research.analyze(hashtag)
        if not result:
            return f"No analysis data for #{hashtag}."
        if isinstance(result, dict):
            lines = [f"#️⃣ Hashtag Analysis: #{hashtag}"]
            for key, val in result.items():
                if isinstance(val, (int, float)) and val > 1000:
                    lines.append(f"  {key}: {val:,.0f}")
                elif val is not None:
                    lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(result)[:800]
    except Exception as e:
        return f"Error analyzing hashtag: {e}"


def handle_suggest_hashtags(args: Dict, ig=None, **kw) -> str:
    """Suggest related hashtags for a given hashtag or topic."""
    hashtag = args.get("hashtag", "").strip().lstrip("#").lower()
    if not hashtag:
        return "Error: 'hashtag' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        suggestions = ig.hashtag_research.suggest(hashtag)
        if not suggestions:
            return f"No suggestions found for #{hashtag}."
        if isinstance(suggestions, list):
            lines = [f"💡 Suggested hashtags for #{hashtag}:"]
            for i, s in enumerate(suggestions[:20], 1):
                if isinstance(s, dict):
                    name = s.get("name", s.get("hashtag", "?"))
                    count = s.get("media_count", s.get("count", 0))
                    lines.append(f"  {i}. #{name} ({count:,} posts)" if count else f"  {i}. #{name}")
                else:
                    lines.append(f"  {i}. #{s}")
            return "\n".join(lines)
        return str(suggestions)[:800]
    except Exception as e:
        return f"Error suggesting hashtags: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: NOTIFICATIONS (2 tools)
# ═══════════════════════════════════════════════════════════

def handle_get_notifications(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get recent notifications/activity."""
    if not is_logged_in:
        return "❌ Login required to view notifications."
    try:
        notifs = ig.notifications.get_all_parsed()
        if not notifs:
            return "No notifications found."
        items = notifs if isinstance(notifs, list) else [notifs]
        lines = [f"🔔 Notifications ({len(items)} items):"]
        for i, n in enumerate(items[:15], 1):
            if isinstance(n, dict):
                ntype = n.get("type", "?")
                user = n.get("username", n.get("user", "?"))
                text = n.get("text", n.get("message", ""))[:80]
                lines.append(f"  {i}. [{ntype}] @{user}: {text}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting notifications: {e}"


def handle_get_activity_counts(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get activity count summary (likes, comments, follows)."""
    if not is_logged_in:
        return "❌ Login required to view activity counts."
    try:
        counts = ig.notifications.get_counts_parsed()
        if not counts:
            return "No activity counts available."
        if isinstance(counts, dict):
            lines = ["📊 Activity Counts:"]
            for key, val in counts.items():
                lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(counts)[:500]
    except Exception as e:
        return f"Error getting activity counts: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: PUBLIC DATA ANALYTICS (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_compare_profiles(args: Dict, ig=None, **kw) -> str:
    """Compare two or more Instagram profiles side by side."""
    usernames = args.get("usernames", [])
    if isinstance(usernames, str):
        usernames = [u.strip().lstrip("@").lower() for u in usernames.split(",")]
    if len(usernames) < 2:
        return "Error: At least 2 usernames are required. Example: ['nike', 'adidas']"
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.public_data.compare_profiles(usernames)
        if not result:
            return "Comparison failed — no data returned."
        if isinstance(result, dict):
            lines = [f"📊 Profile Comparison ({len(usernames)} accounts):"]
            for key, val in result.items():
                if isinstance(val, dict):
                    lines.append(f"\n  {key}:")
                    for k2, v2 in val.items():
                        lines.append(f"    {k2}: {v2}")
                else:
                    lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(result)[:1500]
    except Exception as e:
        return f"Error comparing profiles: {e}"


def handle_engagement_analysis(args: Dict, ig=None, **kw) -> str:
    """Analyze engagement rate and metrics for a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.public_data.engagement_analysis(username)
        if not result:
            return f"No engagement data for @{username}."
        if isinstance(result, dict):
            lines = [f"📈 Engagement Analysis: @{username}"]
            for key, val in result.items():
                if isinstance(val, float):
                    lines.append(f"  {key}: {val:.2f}%")
                elif isinstance(val, int) and val > 1000:
                    lines.append(f"  {key}: {val:,}")
                elif val is not None:
                    lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(result)[:800]
    except Exception as e:
        return f"Error analyzing engagement: {e}"


def handle_build_report(args: Dict, ig=None, **kw) -> str:
    """Build a comprehensive analytics report for a user."""
    username = args.get("username", "").strip().lstrip("@").lower()
    if not username:
        return "Error: 'username' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        result = ig.public_data.build_report(username)
        if not result:
            return f"No report data for @{username}."
        if isinstance(result, dict):
            lines = [f"📋 Full Report: @{username}"]
            for key, val in result.items():
                if isinstance(val, dict):
                    lines.append(f"\n  {key}:")
                    for k2, v2 in list(val.items())[:8]:
                        lines.append(f"    {k2}: {v2}")
                elif isinstance(val, list):
                    lines.append(f"  {key}: [{len(val)} items]")
                else:
                    lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        return str(result)[:1500]
    except Exception as e:
        return f"Error building report: {e}"


