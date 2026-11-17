"""
Parsers
=======
Standalone parsing functions for Instagram API responses.
Used by both AnonClient and AsyncAnonClient — eliminates code duplication.

All functions are pure (no I/O, no self) — they transform dicts/strings.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import orjson as _orjson

    def _loads_json(raw: str) -> Any:
        return _orjson.loads(raw)
except ImportError:
    def _loads_json(raw: str) -> Any:
        return json.loads(raw)

logger = logging.getLogger("instaharvest_v2.parsers")


def parse_count(text: str) -> int:
    """Parse follower count text: '1.2M' -> 1200000."""
    if not text:
        return 0
    text = str(text).replace(",", "").strip()
    multiplier = 1
    if text.endswith(("K", "k")):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith(("M", "m")):
        multiplier = 1000000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def parse_meta_tags(html: str) -> Dict:
    """
    Extract profile data from meta tags and title.

    Current Instagram HTML format (2024+):
    - <title>Full Name (&#064;username) • Instagram photos and videos</title>
    - Meta content contains: "NNN Followers, NNN Following, NNN Posts"
    - og:image has profile picture URL
    """
    import html as html_module
    data = {}

    # --- Username + Full name from <title> ---
    title_match = re.search(r'<title>([^<]*)</title>', html)
    title_text = ""
    if title_match:
        title_text = html_module.unescape(title_match.group(1))
        name_match = re.search(r'^(.+?)\s*\(@(\w+)\)', title_text)
        if name_match:
            data["full_name"] = name_match.group(1).strip()
            data["username"] = name_match.group(2)

    # --- Followers/Following/Posts from ALL meta content attributes ---
    all_content = " ".join(re.findall(r'content="([^"]*)"', html))
    all_content = html_module.unescape(all_content)

    followers_m = re.search(r'([\d,.]+[KMBkmb]?)\s*Followers', all_content, re.IGNORECASE)
    following_m = re.search(r'([\d,.]+[KMBkmb]?)\s*Following', all_content, re.IGNORECASE)
    posts_m = re.search(r'([\d,.]+[KMBkmb]?)\s*Posts', all_content, re.IGNORECASE)

    if followers_m:
        data["followers"] = parse_count(followers_m.group(1))
    if following_m:
        data["following"] = parse_count(following_m.group(1))
    if posts_m:
        data["posts_count"] = parse_count(posts_m.group(1))

    # --- Fallback: try title text for follower counts ---
    if "followers" not in data and title_text:
        tf = re.search(r'([\d,.]+[KMBkmb]?)\s*Followers', title_text, re.IGNORECASE)
        tg = re.search(r'([\d,.]+[KMBkmb]?)\s*Following', title_text, re.IGNORECASE)
        tp = re.search(r'([\d,.]+[KMBkmb]?)\s*Posts', title_text, re.IGNORECASE)
        if tf:
            data["followers"] = parse_count(tf.group(1))
        if tg:
            data["following"] = parse_count(tg.group(1))
        if tp:
            data["posts_count"] = parse_count(tp.group(1))

    # --- Bio from description ---
    desc_match = re.search(r'<meta[^>]+(?:name|property)="description"[^>]+content="([^"]*)"', html)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="description"', html)
    if desc_match:
        desc_text = html_module.unescape(desc_match.group(1))
        bio_match = re.search(r'Posts\s*[-–—:]\s*(.*)', desc_text, re.DOTALL)
        if bio_match:
            bio = bio_match.group(1).strip()
            if bio and not re.match(r'^see Instagram photos', bio, re.IGNORECASE):
                data["biography"] = bio

    # --- Fallback bio from og:description ---
    if "biography" not in data:
        og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"', html)
        if not og_desc:
            og_desc = re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="og:description"', html)
        if og_desc:
            desc = html_module.unescape(og_desc.group(1))
            if desc and not re.match(r'^\d+[\d,.]*[KMBkmb]?\s*Followers', desc, re.IGNORECASE):
                data["biography"] = desc

    # --- Fallback bio: use full title text ---
    if "biography" not in data and title_text and data.get("username"):
        data["biography"] = title_text

    # --- Profile picture from og:image ---
    og_image = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]*)"', html)
    if not og_image:
        og_image = re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="og:image"', html)
    if og_image:
        data["profile_pic_url"] = html_module.unescape(og_image.group(1))

    return data


def parse_graphql_user(user: Dict) -> Dict:
    """Parse GraphQL user object into clean format with ALL available fields.

    Extracts every useful field from web_profile_info response:
    - Basic profile (username, bio, followers, etc.)
    - Business info (email, phone, address, category)
    - Content flags (clips, guides, IGTV, channel)
    - Related profiles (edge_related_profiles)
    - Recent posts with full data (tags, mentions, carousel)
    """
    edges_media = user.get("edge_owner_to_timeline_media", {})

    # Related profiles
    related_profiles = []
    for edge in user.get("edge_related_profiles", {}).get("edges", []):
        node = edge.get("node", {})
        related_profiles.append({
            "user_id": node.get("id"),
            "username": node.get("username"),
            "full_name": node.get("full_name"),
            "is_verified": node.get("is_verified", False),
            "is_private": node.get("is_private", False),
            "profile_pic_url": node.get("profile_pic_url"),
        })

    # Business address parsing
    business_address = None
    addr_json = user.get("business_address_json")
    if addr_json:
        try:
            if isinstance(addr_json, str):
                try:
                    import orjson
                    business_address = orjson.loads(addr_json)
                except ImportError:
                    import json as _json
                    business_address = _json.loads(addr_json)
            else:
                business_address = addr_json
        except Exception as e:
            logger.debug(f"business_address JSON decode failed: {e}")
            # Keep raw addr_json as fallback — JSON decode failed
            business_address = addr_json

    return {
        # Core identity
        "user_id": user.get("id"),
        "fbid": user.get("fbid"),
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "biography": user.get("biography"),
        "profile_pic_url": user.get("profile_pic_url"),
        "profile_pic_url_hd": user.get("profile_pic_url_hd"),
        "external_url": user.get("external_url"),
        # Status flags
        "is_private": user.get("is_private", False),
        "is_verified": user.get("is_verified", False),
        "is_business": user.get("is_business_account", False),
        "is_professional_account": user.get("is_professional_account", False),
        "is_joined_recently": user.get("is_joined_recently", False),
        # Counts
        "followers": user.get("edge_followed_by", {}).get("count"),
        "following": user.get("edge_follow", {}).get("count"),
        "posts_count": edges_media.get("count"),
        "highlight_count": user.get("highlight_reel_count", 0),
        "igtv_count": user.get("edge_felix_video_timeline", {}).get("count", 0),
        "mutual_followers": user.get("edge_mutual_followed_by", {}).get("count", 0),
        # Category / business
        "category": user.get("category_name", ""),
        "category_enum": user.get("category_enum", ""),
        "overall_category": user.get("overall_category_name", ""),
        "business_email": user.get("business_email"),
        "business_phone": user.get("business_phone_number"),
        "business_address": business_address,
        "business_contact_method": user.get("business_contact_method"),
        # Content
        "bio_links": user.get("bio_links", []),
        "pronouns": user.get("pronouns", []),
        "has_clips": user.get("has_clips", False),
        "has_guides": user.get("has_guides", False),
        "has_channel": user.get("has_channel", False),
        "show_threads_badge": user.get("show_text_post_app_badge", False),
        # Related profiles
        "related_profiles": related_profiles,
        # Posts
        "recent_posts": parse_timeline_edges(edges_media.get("edges", [])),
        "has_next_page": edges_media.get("page_info", {}).get("has_next_page", False),
        "end_cursor": edges_media.get("page_info", {}).get("end_cursor"),
    }


def parse_timeline_edges(edges: List[Dict]) -> List[Dict]:
    """Parse GraphQL timeline edges into post list with full data extraction.

    Extracts ALL available data from a single web_profile_info response:
    - Post metadata (shortcode, type, timestamps, likes, comments)
    - Carousel media (all slide URLs)
    - Tagged users (edge_media_to_tagged_user)
    - Caption @mentions
    - Post URL
    - Video data (url, views)
    """
    posts = []
    for edge in edges:
        node = edge.get("node", {})
        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
        caption = caption_edges[0]["node"]["text"] if caption_edges else ""

        shortcode = node.get("shortcode")
        typename = node.get("__typename", "")

        # Post type string
        if typename == "GraphSidecar":
            post_type = "carousel"
        elif typename == "GraphVideo" or node.get("is_video"):
            post_type = "video"
        else:
            post_type = "image"

        post = {
            "shortcode": shortcode,
            "post_url": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
            "media_type": typename,
            "post_type": post_type,
            "display_url": node.get("display_url"),
            "thumbnail_url": node.get("thumbnail_src"),
            "is_video": node.get("is_video", False),
            "likes": node.get("edge_liked_by", {}).get("count", 0)
                     or node.get("edge_media_preview_like", {}).get("count", 0),
            "comments": node.get("edge_media_to_comment", {}).get("count", 0),
            "caption": caption,
            "taken_at": node.get("taken_at_timestamp"),
            "pk": node.get("id"),
            "video_url": node.get("video_url"),
            "video_views": node.get("video_view_count"),
            "dimensions": node.get("dimensions"),
            "accessibility_caption": node.get("accessibility_caption", ""),
        }

        # Tagged users (edge_media_to_tagged_user) — available in web_profile_info!
        tagged_edges = node.get("edge_media_to_tagged_user", {}).get("edges", [])
        tagged_users = []
        for te in tagged_edges:
            tag_user = te.get("node", {}).get("user", {})
            tag_username = tag_user.get("username", "")
            if tag_username:
                tagged_users.append(tag_username.lower())
        post["tagged_users"] = tagged_users

        # Caption @mentions
        mentions = re.findall(r'@([a-zA-Z0-9_.]+)', caption) if caption else []
        post["mentions"] = [m.lower() for m in mentions]

        # Coauthor producers
        coauthors = node.get("coauthor_producers", []) or []
        if coauthors:
            post["coauthor_producers"] = [
                {"username": co.get("username", ""), "user_id": co.get("id")}
                for co in coauthors
            ]

        # Pinned post detection
        pinned = node.get("pinned_for_users", []) or []
        if pinned:
            post["is_pinned"] = True

        # Location
        location = node.get("location")
        if location and isinstance(location, dict):
            post["location"] = {
                "id": location.get("id"),
                "name": location.get("name"),
                "slug": location.get("slug"),
                "has_public_page": location.get("has_public_page"),
            }

        # Carousel (GraphSidecar)
        sidecar = node.get("edge_sidecar_to_children", {})
        if sidecar:
            children = []
            for child_edge in sidecar.get("edges", []):
                child = child_edge.get("node", {})
                child_data = {
                    "pk": child.get("id"),
                    "shortcode": child.get("shortcode"),
                    "display_url": child.get("display_url"),
                    "is_video": child.get("is_video", False),
                    "video_url": child.get("video_url"),
                    "media_type": child.get("__typename"),
                    "accessibility_caption": child.get("accessibility_caption", ""),
                    "display_resources": [
                        {"url": r.get("src"), "width": r.get("config_width"), "height": r.get("config_height")}
                        for r in child.get("display_resources", [])
                    ],
                }
                # Carousel child usertags
                child_tagged = child.get("edge_media_to_tagged_user", {}).get("edges", [])
                if child_tagged:
                    child_data["tagged_users"] = [
                        ct.get("node", {}).get("user", {}).get("username", "").lower()
                        for ct in child_tagged
                        if ct.get("node", {}).get("user", {}).get("username")
                    ]
                children.append(child_data)
            post["carousel_media"] = children
            post["carousel_count"] = len(children)

        posts.append(post)
    return posts


def parse_embed_media(media: Dict) -> Dict:
    """Parse shortcode_media from embed data."""
    owner = media.get("owner", {})
    caption_edges = media.get("edge_media_to_caption", {}).get("edges", [])
    caption = caption_edges[0]["node"]["text"] if caption_edges else ""

    images = []
    if media.get("display_url"):
        images.append({"url": media["display_url"]})
    for res in media.get("display_resources", []):
        images.append({
            "url": res.get("src"),
            "width": res.get("config_width"),
            "height": res.get("config_height"),
        })

    shortcode = media.get("shortcode")

    # Tagged users
    tagged_edges = media.get("edge_media_to_tagged_user", {}).get("edges", [])
    tagged_users = [
        te.get("node", {}).get("user", {}).get("username", "").lower()
        for te in tagged_edges
        if te.get("node", {}).get("user", {}).get("username")
    ]

    # Caption @mentions
    mentions = [m.lower() for m in re.findall(r'@([a-zA-Z0-9_.]+)', caption)] if caption else []

    return {
        "pk": media.get("id"),
        "shortcode": shortcode,
        "post_url": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
        "media_type": media.get("__typename"),
        "is_video": media.get("is_video", False),
        "caption": caption,
        "likes": media.get("edge_media_preview_like", {}).get("count", 0),
        "comments_count": media.get("edge_media_preview_comment", {}).get("count", 0) or
                          media.get("edge_media_to_parent_comment", {}).get("count", 0),
        "taken_at": media.get("taken_at_timestamp"),
        "owner": {
            "username": owner.get("username"),
            "pk": owner.get("id"),
            "is_verified": owner.get("is_verified"),
            "profile_pic_url": owner.get("profile_pic_url"),
        },
        "tagged_users": tagged_users,
        "mentions": mentions,
        "images": images,
        "video_url": media.get("video_url"),
        "video_views": media.get("video_view_count"),
    }


def parse_embed_html(html: str, shortcode: str) -> Dict:
    """Fallback: parse embed HTML tags."""
    data = {"shortcode": shortcode}

    caption_match = re.search(
        r'<div class="Caption"[^>]*>.*?<div class="CaptionTextContainer"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )
    if caption_match:
        caption_html = caption_match.group(1)
        data["caption"] = re.sub(r'<[^>]+>', '', caption_html).strip()

    user_match = re.search(r'<a[^>]*class="UserName"[^>]*>([^<]+)</a>', html)
    if user_match:
        data["owner"] = {"username": user_match.group(1).strip()}

    likes_match = re.search(r'<button[^>]*>.*?([\d,]+)\s*likes?', html, re.DOTALL | re.IGNORECASE)
    if likes_match:
        data["likes"] = int(likes_match.group(1).replace(",", ""))

    img_match = re.search(r'<img[^>]+class="[^"]*EmbeddedMedia[^"]*"[^>]+src="([^"]+)"', html)
    if img_match:
        data["images"] = [{"url": img_match.group(1)}]

    return data if len(data) > 1 else {}


def parse_mobile_feed_item(item: Dict) -> Dict:
    """
    Parse mobile API feed item into clean format.

    Mobile API returns different field names than GraphQL:
    - like_count (not edge_liked_by)
    - comment_count (not edge_media_to_comment)
    - carousel_media (not edge_sidecar_to_children)
    - image_versions2 (not display_url)
    """
    caption_obj = item.get("caption") or {}
    caption_text = caption_obj.get("text", "") if isinstance(caption_obj, dict) else ""

    image_url = ""
    image_versions = item.get("image_versions2", {})
    candidates = image_versions.get("candidates", [])
    if candidates:
        best = max(candidates, key=lambda c: c.get("width", 0) * c.get("height", 0))
        image_url = best.get("url", "")

    media_type_map = {1: "GraphImage", 2: "GraphVideo", 8: "GraphSidecar"}
    post_type_map = {1: "image", 2: "video", 8: "carousel"}
    raw_type = item.get("media_type", 1)

    shortcode = item.get("code")

    # Caption @mentions
    mentions = [m.lower() for m in re.findall(r'@([a-zA-Z0-9_.]+)', caption_text)] if caption_text else []

    result = {
        "pk": str(item.get("pk", "")),
        "id": item.get("id"),
        "shortcode": shortcode,
        "post_url": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
        "media_type": media_type_map.get(raw_type, f"type_{raw_type}"),
        "post_type": post_type_map.get(raw_type, "image"),
        "media_type_raw": raw_type,
        "display_url": image_url,
        "is_video": raw_type == 2,
        "likes": item.get("like_count", 0),
        "comments": item.get("comment_count", 0),
        "caption": caption_text,
        "mentions": mentions,
        "taken_at": item.get("taken_at"),
        "accessibility_caption": item.get("accessibility_caption", ""),
    }

    # Video data
    if raw_type == 2:
        video_versions = item.get("video_versions", [])
        if video_versions:
            result["video_url"] = video_versions[0].get("url", "")
        result["video_duration"] = item.get("video_duration")
        result["video_views"] = item.get("view_count") or item.get("play_count")

    # Carousel media
    carousel = item.get("carousel_media", [])
    if carousel:
        children = []
        for child in carousel:
            child_img = ""
            child_versions = child.get("image_versions2", {})
            child_candidates = child_versions.get("candidates", [])
            if child_candidates:
                best_child = max(child_candidates, key=lambda c: c.get("width", 0) * c.get("height", 0))
                child_img = best_child.get("url", "")

            child_data = {
                "pk": str(child.get("pk", "")),
                "display_url": child_img,
                "is_video": child.get("media_type") == 2,
                "media_type": media_type_map.get(child.get("media_type", 1), "unknown"),
            }

            if child.get("media_type") == 2:
                child_vv = child.get("video_versions", [])
                if child_vv:
                    child_data["video_url"] = child_vv[0].get("url", "")
                child_data["video_duration"] = child.get("video_duration")

            children.append(child_data)

        result["carousel_media"] = children
        result["carousel_count"] = len(children)

    # Location
    location = item.get("location")
    if location and isinstance(location, dict):
        result["location"] = {
            "pk": location.get("pk"),
            "name": location.get("name"),
            "city": location.get("city"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
        }

    # User tags
    usertags = item.get("usertags", {})
    if usertags and usertags.get("in"):
        result["tagged_users"] = [
            tag.get("user", {}).get("username", "")
            for tag in usertags["in"]
            if tag.get("user")
        ]

    return result


def parse_graphql_docid_media(media: Dict) -> Dict:
    """
    Parse xdt_shortcode_media from GraphQL doc_id response.
    Returns a standardized dict compatible with other strategies.
    """
    owner = media.get("owner", {})
    caption_edges = media.get("edge_media_to_caption", {}).get("edges", [])
    caption = caption_edges[0]["node"]["text"] if caption_edges else ""

    result = {
        "_strategy": "graphql_docid",
        "pk": media.get("id"),
        "shortcode": media.get("shortcode"),
        "post_url": f"https://www.instagram.com/p/{media.get('shortcode')}/" if media.get("shortcode") else "",
        "media_type": media.get("__typename"),
        "product_type": media.get("product_type"),
        "is_video": media.get("is_video", False),
        "caption": caption,
        "likes": media.get("edge_media_preview_like", {}).get("count", 0),
        "comments_count": (
            media.get("edge_media_preview_comment", {}).get("count", 0)
            or media.get("edge_media_to_parent_comment", {}).get("count", 0)
        ),
        "taken_at": media.get("taken_at_timestamp"),
        "display_url": media.get("display_url"),
        "thumbnail_src": media.get("thumbnail_src"),
        "dimensions": media.get("dimensions"),
        "owner": {
            "pk": owner.get("id"),
            "username": owner.get("username"),
            "full_name": owner.get("full_name"),
            "is_verified": owner.get("is_verified"),
            "is_private": owner.get("is_private"),
            "profile_pic_url": owner.get("profile_pic_url"),
            "followers": owner.get("edge_followed_by", {}).get("count"),
            "posts_count": owner.get("edge_owner_to_timeline_media", {}).get("count"),
        },
        "video_url": media.get("video_url"),
        "video_view_count": media.get("video_view_count"),
        "video_play_count": media.get("video_play_count"),
        "video_duration": media.get("video_duration"),
        "has_audio": media.get("has_audio"),
        "display_resources": [
            {
                "url": r.get("src"),
                "width": r.get("config_width"),
                "height": r.get("config_height"),
            }
            for r in media.get("display_resources", [])
        ],
        "location": media.get("location"),
        "is_paid_partnership": media.get("is_paid_partnership"),
    }

    # Tagged users
    tagged_edges = media.get("edge_media_to_tagged_user", {}).get("edges", [])
    if tagged_edges:
        result["tagged_users"] = [
            te.get("node", {}).get("user", {}).get("username", "").lower()
            for te in tagged_edges
            if te.get("node", {}).get("user", {}).get("username")
        ]

    # Caption @mentions
    if caption:
        cap_mentions = [m.lower() for m in re.findall(r'@([a-zA-Z0-9_.]+)', caption)]
        if cap_mentions:
            result["mentions"] = cap_mentions

    # Music info for reels
    music = media.get("clips_music_attribution_info")
    if music:
        result["audio"] = {
            "title": music.get("song_name"),
            "artist": music.get("artist_name"),
            "audio_id": music.get("audio_id"),
            "uses_original_audio": music.get("uses_original_audio"),
        }

    # Carousel (sidecar)
    sidecar = media.get("edge_sidecar_to_children")
    if sidecar:
        children = []
        for edge in sidecar.get("edges", []):
            child = edge.get("node", {})
            children.append({
                "pk": child.get("id"),
                "shortcode": child.get("shortcode"),
                "display_url": child.get("display_url"),
                "is_video": child.get("is_video", False),
                "video_url": child.get("video_url"),
                "media_type": child.get("__typename"),
                "dimensions": child.get("dimensions"),
                "display_resources": [
                    {
                        "url": r.get("src"),
                        "width": r.get("config_width"),
                        "height": r.get("config_height"),
                    }
                    for r in child.get("display_resources", [])
                ],
            })
        result["carousel_media"] = children
        result["carousel_count"] = len(children)

    return result


# ═══════════════════════════════════════════════════════════════
# 2025/2026 SSR `data-sjs` HTML PARSERS (shared sync & async)
# ═══════════════════════════════════════════════════════════════

_SJS_SCRIPT_RE = re.compile(
    r'<script\b[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _iter_sjs_scripts(html: str, *markers: str) -> List[Any]:
    """Parse `<script type="application/json">` blocks matching any substring marker."""
    if not html:
        return []
    parsed: List[Any] = []
    for raw in _SJS_SCRIPT_RE.findall(html):
        if markers and not any(m in raw for m in markers):
            continue
        try:
            parsed.append(_loads_json(raw))
        except Exception:
            continue
    return parsed


def _find_key_values(obj: Any, key: str) -> List[Any]:
    """Recursively collect all values for `key` inside nested dicts/lists."""
    found: List[Any] = []
    stack: List[Any] = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if key in cur:
                found.append(cur[key])
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return found


def _parse_polaris_media_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Polaris / XIG / XDT SSR media node into a standard post dict."""
    caption_raw = node.get("caption")
    if isinstance(caption_raw, dict):
        caption = caption_raw.get("text", "") or ""
    elif isinstance(caption_raw, str):
        caption = caption_raw
    else:
        caption = ""

    shortcode = node.get("code") or node.get("shortcode") or ""
    typename = node.get("__typename", "")
    raw_type = node.get("media_type")
    video_versions = node.get("video_versions") or []
    carousel_raw = node.get("carousel_media") or []

    is_video = (
        raw_type == 2
        or "Video" in typename
        or bool(video_versions)
        or node.get("product_type") == "clips"
    )
    if raw_type == 8 or "Sidecar" in typename or carousel_raw:
        post_type = "carousel"
        media_type = "GraphSidecar"
    elif is_video:
        post_type = "video"
        media_type = "GraphVideo"
    else:
        post_type = "image"
        media_type = "GraphImage"

    images: List[Dict[str, Any]] = []
    img_v2 = node.get("image_versions2") or {}
    candidates = img_v2.get("candidates") or []
    for cand in candidates:
        if isinstance(cand, dict) and cand.get("url"):
            images.append({
                "url": cand["url"],
                "width": cand.get("width"),
                "height": cand.get("height"),
            })
    display_uri = node.get("display_uri") or node.get("display_url") or ""
    if not display_uri and images:
        best_img = max(images, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
        display_uri = best_img.get("url", "")
    if display_uri and not images:
        images.append({
            "url": display_uri,
            "width": node.get("original_width"),
            "height": node.get("original_height"),
        })

    video_url = None
    if isinstance(video_versions, list) and video_versions:
        first_v = video_versions[0]
        if isinstance(first_v, dict):
            video_url = first_v.get("url")

    likes = node.get("like_count") or 0
    comments_count = node.get("comment_count") or 0
    pk = str(node.get("pk") or node.get("id") or "")
    mentions = [m.lower() for m in re.findall(r'@([a-zA-Z0-9_.]+)', caption)] if caption else []

    post: Dict[str, Any] = {
        "pk": pk,
        "id": node.get("id") or pk,
        "shortcode": shortcode,
        "post_url": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
        "media_type": media_type,
        "post_type": post_type,
        "product_type": node.get("product_type"),
        "display_url": display_uri,
        "thumbnail_url": display_uri,
        "images": images,
        "is_video": is_video,
        "likes": likes,
        "comments": comments_count,
        "comments_count": comments_count,
        "caption": caption,
        "taken_at": node.get("taken_at"),
        "accessibility_caption": node.get("accessibility_caption", "") or "",
        "mentions": mentions,
    }
    if video_url:
        post["video_url"] = video_url
    if node.get("play_count") is not None or node.get("view_count") is not None:
        post["play_count"] = node.get("play_count") or node.get("view_count")
        post["video_views"] = post["play_count"]
    if node.get("original_width") and node.get("original_height"):
        post["dimensions"] = {
            "width": node["original_width"],
            "height": node["original_height"],
        }

    user = node.get("user") or node.get("owner")
    if isinstance(user, dict) and (user.get("username") or user.get("pk") or user.get("id")):
        post["owner"] = {
            "pk": str(user.get("pk") or user.get("id") or ""),
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "is_verified": user.get("is_verified"),
            "profile_pic_url": user.get("profile_pic_url"),
        }

    loc = node.get("location")
    if isinstance(loc, dict):
        post["location"] = {
            "pk": loc.get("pk") or loc.get("id"),
            "name": loc.get("name"),
            "city": loc.get("city"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
        }

    usertags = node.get("usertags") or {}
    if isinstance(usertags, dict) and usertags.get("in"):
        post["tagged_users"] = [
            t.get("user", {}).get("username", "").lower()
            for t in usertags["in"]
            if isinstance(t, dict) and t.get("user", {}).get("username")
        ]

    if carousel_raw:
        children = []
        for child in carousel_raw:
            if not isinstance(child, dict):
                continue
            c_imgs = (child.get("image_versions2") or {}).get("candidates") or []
            c_best = max(c_imgs, key=lambda x: (x.get("width") or 0) * (x.get("height") or 0)) if c_imgs else {}
            c_vv = child.get("video_versions") or []
            c_is_vid = child.get("media_type") == 2 or bool(c_vv)
            children.append({
                "pk": str(child.get("pk") or child.get("id") or ""),
                "display_url": c_best.get("url", ""),
                "is_video": c_is_vid,
                "video_url": c_vv[0].get("url") if c_vv and isinstance(c_vv[0], dict) else None,
                "display_resources": [
                    {"url": r.get("url"), "width": r.get("width"), "height": r.get("height")}
                    for r in c_imgs if isinstance(r, dict) and r.get("url")
                ],
            })
        if children:
            post["carousel_media"] = children
            post["carousel_count"] = len(children)

    return post


def parse_profile_sjs(html: str) -> Dict[str, Any]:
    """Extract profile metadata and timeline posts from SSR `xig_user_by_username` JSON."""
    scripts = _iter_sjs_scripts(html, "xig_user_by_username")
    if not scripts:
        return {}

    result: Dict[str, Any] = {}
    recent_posts: List[Dict[str, Any]] = []
    seen_codes = set()

    for tree in scripts:
        for user_obj in _find_key_values(tree, "xig_user_by_username"):
            if not isinstance(user_obj, dict):
                continue
            if user_obj.get("username") or user_obj.get("follower_count") is not None:
                pk = user_obj.get("pk") or user_obj.get("id")
                if pk and not result.get("user_id"):
                    result["user_id"] = str(pk)
                    result["pk"] = str(pk)
                if user_obj.get("id") and not result.get("fbid"):
                    result["fbid"] = str(user_obj["id"])
                for src_k, dst_k in (
                    ("username", "username"),
                    ("full_name", "full_name"),
                    ("biography", "biography"),
                    ("profile_pic_url", "profile_pic_url"),
                    ("is_private", "is_private"),
                    ("is_verified", "is_verified"),
                    ("follower_count", "followers"),
                    ("following_count", "following"),
                    ("all_media_count", "posts_count"),
                    ("bio_links", "bio_links"),
                    ("has_any_clips", "has_clips"),
                ):
                    val = user_obj.get(src_k)
                    if val is not None and (dst_k not in result or result[dst_k] in (None, "")):
                        result[dst_k] = val

            timeline = user_obj.get("polaris_ordered_timeline_connection")
            if isinstance(timeline, dict):
                for edge in timeline.get("edges") or []:
                    node = edge.get("node") if isinstance(edge, dict) else None
                    if not isinstance(node, dict):
                        continue
                    post = _parse_polaris_media_node(node)
                    key = post.get("shortcode") or post.get("pk")
                    if key and key not in seen_codes:
                        seen_codes.add(key)
                        recent_posts.append(post)

    if recent_posts:
        result["recent_posts"] = recent_posts
    return result


def parse_profile_html(html: str, username: str = "") -> Optional[Dict[str, Any]]:
    """
    Parse Instagram profile HTML across legacy and 2025/2026 SSR formats.

    Shared by AnonClient.get_profile_html and AsyncAnonClient.get_profile_html.
    Distinguishes true login redirects from public profile SSR pages that
    embed navigation/footer `login/?next=` links.
    """
    if not html:
        return None

    result: Dict[str, Any] = {}

    # Method 1: window._sharedData
    shared_data_match = re.search(
        r'window\._sharedData\s*=\s*({.+?})\s*;</script>',
        html, re.DOTALL,
    )
    if shared_data_match:
        try:
            shared = _loads_json(shared_data_match.group(1))
            user_data = (
                shared.get("entry_data", {})
                .get("ProfilePage", [{}])[0]
                .get("graphql", {})
                .get("user", {})
            )
            if user_data:
                result = parse_graphql_user(user_data)
        except Exception:
            pass

    # Method 2: window.__additionalDataLoaded
    if not result:
        additional_match = re.search(
            r'window\.__additionalDataLoaded\s*\(\s*[\'"].*?[\'"]\s*,\s*({.+?})\s*\)\s*;',
            html, re.DOTALL,
        )
        if additional_match:
            try:
                data = _loads_json(additional_match.group(1))
                user_data = data.get("graphql", {}).get("user", {}) or data.get("user", {})
                if user_data:
                    result = parse_graphql_user(user_data)
            except Exception:
                pass

    # Method 3: 2025/2026 SSR `data-sjs` Relay payload (`xig_user_by_username`)
    if not result:
        result = parse_profile_sjs(html)

    # Method 4: JSON-LD schema
    if not result:
        ld_match = re.search(
            r'<script type="application/ld\+json">\s*({.+?})\s*</script>',
            html, re.DOTALL,
        )
        if ld_match:
            try:
                ld = _loads_json(ld_match.group(1))
                result = {
                    "username": ld.get("alternateName", "").lstrip("@"),
                    "full_name": ld.get("name", ""),
                    "biography": ld.get("description", ""),
                    "profile_pic_url": ld.get("image", ""),
                    "url": ld.get("url", ""),
                }
            except Exception:
                pass

    # Method 5: Meta tags fallback & enrichment
    meta_data = parse_meta_tags(html)
    if not result:
        result = meta_data
    elif meta_data:
        for key in ("followers", "following", "posts_count"):
            if not result.get(key) and meta_data.get(key):
                result[key] = meta_data[key]
        if not result.get("posts_count") and result.get("recent_posts"):
            result["posts_count"] = len(result["recent_posts"])
        for key in ("full_name", "biography", "profile_pic_url", "is_verified", "is_private"):
            if not result.get(key) and meta_data.get(key):
                result[key] = meta_data[key]

    # Guard against true login redirects while allowing public SSR pages with login links
    has_login_marker = '"LoginAndSignupPage"' in html or "login/?next=" in html
    has_profile_identity = bool(
        result.get("username")
        or result.get("user_id")
        or result.get("pk")
        or result.get("followers")
    )
    if has_login_marker and not has_profile_identity:
        return None

    if result:
        result["_strategy"] = "html_parse"
        if username:
            result["_username"] = username
        return result

    return None


def parse_polaris_media_sjs(html: str, shortcode: str = "") -> Optional[Dict[str, Any]]:
    """Extract post metadata, media URLs, and preview comments from `/p/{shortcode}/` SSR HTML."""
    for tree in _iter_sjs_scripts(html, "xig_polaris_media"):
        for pm in _find_key_values(tree, "xig_polaris_media"):
            if not isinstance(pm, dict):
                continue
            media_node = pm.get("if_not_gated_logged_out")
            if not isinstance(media_node, dict):
                media_node = pm
            if not (media_node.get("pk") or media_node.get("code")):
                continue

            post = _parse_polaris_media_node(media_node)
            post["_strategy"] = "html_parse"
            if shortcode and not post.get("shortcode"):
                post["shortcode"] = shortcode
                post["post_url"] = f"https://www.instagram.com/p/{shortcode}/"

            # Extract preview comments from comments_connection
            comments_conn = pm.get("comments_connection") or {}
            parsed_comments: List[Dict[str, Any]] = []
            for edge in comments_conn.get("edges") or []:
                cnode = edge.get("node") if isinstance(edge, dict) else None
                if not isinstance(cnode, dict):
                    continue
                cuser = cnode.get("user") or {}
                parsed_comments.append({
                    "pk": cnode.get("pk") or cnode.get("id"),
                    "text": cnode.get("text", ""),
                    "username": cuser.get("username", ""),
                    "user_pk": cuser.get("pk") or cuser.get("id"),
                    "is_verified": cuser.get("is_verified", False),
                    "profile_pic_url": cuser.get("profile_pic_url"),
                    "likes": cnode.get("comment_like_count", 0),
                    "created_at": cnode.get("created_at"),
                })
            if parsed_comments:
                post["comments"] = parsed_comments
            return post
    return None


def parse_hashtag_sjs(html: str, tag_name: str) -> Optional[Dict[str, Any]]:
    """Extract hashtag posts from `/explore/tags/{tag}/` SSR HTML."""
    tag = tag_name.lstrip("#").strip().lower()
    for tree in _iter_sjs_scripts(html, "xig_logged_out_popular_search_media_info"):
        for info in _find_key_values(tree, "xig_logged_out_popular_search_media_info"):
            if not isinstance(info, dict):
                continue
            edges = info.get("edges") or []
            posts = [
                _parse_polaris_media_node(e["node"])
                for e in edges
                if isinstance(e, dict) and isinstance(e.get("node"), dict)
            ]
            if posts:
                page_info = info.get("page_info") or {}
                return {
                    "tag_name": tag,
                    "posts": posts,
                    "more_available": bool(page_info.get("has_next_page")),
                    "next_max_id": page_info.get("end_cursor"),
                    "next_page": None,
                    "media_count": len(posts),
                }
    return None


def parse_location_sjs(html: str, location_id: Union[int, str]) -> Optional[Dict[str, Any]]:
    """Extract location metadata and posts from `/explore/locations/{id}/` SSR HTML."""
    scripts = _iter_sjs_scripts(html, "xdt_location_get_web_info")
    if not scripts:
        return None

    loc_dict: Optional[Dict[str, Any]] = None
    posts: List[Dict[str, Any]] = []
    more_available = False
    next_max_id = None
    media_count = 0

    for tree in scripts:
        for info in _find_key_values(tree, "xdt_location_get_web_info"):
            if not isinstance(info, dict):
                continue
            li = (info.get("native_location_data") or {}).get("location_info") or {}
            if li:
                media_count = li.get("media_count") or 0
                loc_dict = {
                    "pk": li.get("location_id") or str(location_id),
                    "name": li.get("name"),
                    "address": li.get("location_address"),
                    "city": li.get("location_city"),
                    "lat": li.get("lat"),
                    "lng": li.get("lng"),
                    "slug": li.get("slug"),
                    "category": li.get("category"),
                }
        for tab in _find_key_values(tree, "xdt_location_get_web_info_tab"):
            if not isinstance(tab, dict):
                continue
            edges = tab.get("edges") or []
            for edge in edges:
                node = edge.get("node") if isinstance(edge, dict) else None
                if isinstance(node, dict):
                    posts.append(_parse_polaris_media_node(node))
            page_info = tab.get("page_info") or {}
            more_available = bool(page_info.get("has_next_page"))
            next_max_id = page_info.get("end_cursor")

    if loc_dict or posts:
        return {
            "location": loc_dict,
            "posts": posts,
            "more_available": more_available,
            "next_max_id": next_max_id,
            "media_count": media_count or len(posts),
        }
    return None


def needs_post_html_fallback(post: Any) -> bool:
    """Return True if post lookup is missing or only an incomplete embed stub."""
    if not post or not isinstance(post, dict):
        return True
    return post.get("_strategy") == "embed" and not (
        post.get("likes") or post.get("caption") or post.get("owner") or post.get("video_url")
    )


def merge_unique_posts(target: List[Dict[str, Any]], seen_pks: set, posts: List[Dict[str, Any]]) -> int:
    """Append deduplicated posts into `target` and return count added."""
    added = 0
    for p in posts:
        if not isinstance(p, dict):
            continue
        pk = p.get("pk") or p.get("shortcode")
        if pk and pk not in seen_pks:
            seen_pks.add(pk)
            target.append(p)
            added += 1
    return added


_POLARIS_VIEWER_RE = re.compile(r'"PolarisViewer"\s*,\s*\[\]\s*,\s*(\{.*?\})\s*,\s*\d+')
_WEB_REV_RE = re.compile(
    r'"server_revision"\s*:\s*(\d+)|"rollout_hash"\s*:\s*"([a-f0-9]+)"|"consistency"\s*:\s*\{\s*"rev"\s*:\s*(\d+)'
)
_WEB_DOC_ID_RE = re.compile(r'"(?:doc_id|queryID)"\s*:\s*"(\d{15,22})"')


def parse_polaris_viewer(html: str) -> Optional[Dict[str, Any]]:
    """Extract logged-in viewer profile dict (`PolarisViewer`) from web HTML."""
    if not html:
        return None
    for match in _POLARIS_VIEWER_RE.finditer(html):
        try:
            payload = _loads_json(match.group(1))
        except Exception:
            continue
        if isinstance(payload, dict):
            data = payload.get("data", payload)
            if isinstance(data, dict) and (data.get("username") or data.get("id")):
                return data
    # Fallback scan through parsed JSON script blocks
    for tree in _iter_sjs_scripts(html, "PolarisViewer"):
        for val in _find_key_values(tree, "PolarisViewer"):
            if isinstance(val, dict):
                data = val.get("data", val)
                if isinstance(data, dict) and (data.get("username") or data.get("id")):
                    return data
    return None


def parse_web_revision(html: str) -> Optional[str]:
    """Extract current Instagram web build/consistency revision from HTML."""
    if not html:
        return None
    match = _WEB_REV_RE.search(html)
    if match:
        return match.group(1) or match.group(2) or match.group(3)
    return None


def parse_web_doc_ids(html: str) -> List[str]:
    """Extract unique Relay/GraphQL doc_ids embedded in Instagram web HTML."""
    if not html:
        return []
    return list(dict.fromkeys(_WEB_DOC_ID_RE.findall(html)))


def apply_web_html_metadata(html: str, sess: Any = None) -> Optional[Dict[str, Any]]:
    """
    Extract revision and PolarisViewer profile from Instagram home HTML and
    sync them onto `sess` when present.
    """
    if not isinstance(html, str) or not html:
        return None
    rev = parse_web_revision(html)
    if rev and sess is not None and hasattr(sess, "x_instagram_ajax"):
        sess.x_instagram_ajax = rev
    viewer = parse_polaris_viewer(html)
    if viewer and sess is not None and viewer.get("username") and hasattr(sess, "username"):
        sess.username = viewer["username"]
    return viewer


def build_session_verification_report(html: str, sess: Any) -> Dict[str, Any]:
    """
    Validate a live web session from Instagram home HTML without logging secrets.

    Populates `sess.username` and `sess.x_instagram_ajax` when available.
    """
    viewer = apply_web_html_metadata(html, sess=sess)
    is_logged_in = isinstance(html, str) and bool(html) and (
        bool(viewer) or ("not-logged-in" not in html[:600].lower() and "LoginAndSignupPage" not in html[:4000])
    )
    rev = getattr(sess, "x_instagram_ajax", "") or parse_web_revision(html or "") or ""
    return {
        "valid": bool(is_logged_in),
        "ds_user_id": getattr(sess, "ds_user_id", "") or "",
        "username": (viewer or {}).get("username") or getattr(sess, "username", "") or "",
        "full_name": (viewer or {}).get("full_name", ""),
        "is_private": bool((viewer or {}).get("is_private", False)),
        "server_revision": rev,
        "has_dtsg": bool(getattr(sess, "fb_dtsg", "") or (isinstance(html, str) and "DTSGInitialData" in html)),
        "has_claim": bool(getattr(sess, "ig_www_claim", "")),
        "live_doc_ids": parse_web_doc_ids(html) if isinstance(html, str) else [],
    }
