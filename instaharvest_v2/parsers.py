"""
Parsers
=======
Standalone parsing functions for Instagram API responses.
Used by both AnonClient and AsyncAnonClient — eliminates code duplication.

All functions are pure (no I/O, no self) — they transform dicts/strings.
"""

import re
from typing import Dict, List


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
    """Parse GraphQL user object into clean format."""
    edges_media = user.get("edge_owner_to_timeline_media", {})
    return {
        "user_id": user.get("id"),
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "biography": user.get("biography"),
        "profile_pic_url": user.get("profile_pic_url"),
        "profile_pic_url_hd": user.get("profile_pic_url_hd"),
        "is_private": user.get("is_private", False),
        "is_verified": user.get("is_verified", False),
        "is_business": user.get("is_business_account", False),
        "category": user.get("category_name", ""),
        "external_url": user.get("external_url"),
        "followers": user.get("edge_followed_by", {}).get("count"),
        "following": user.get("edge_follow", {}).get("count"),
        "posts_count": edges_media.get("count"),
        "bio_links": user.get("bio_links", []),
        "pronouns": user.get("pronouns", []),
        "highlight_count": user.get("highlight_reel_count", 0),
        "recent_posts": parse_timeline_edges(edges_media.get("edges", [])),
    }


def parse_timeline_edges(edges: List[Dict]) -> List[Dict]:
    """Parse GraphQL timeline edges into post list (with carousel support)."""
    posts = []
    for edge in edges:
        node = edge.get("node", {})
        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
        caption = caption_edges[0]["node"]["text"] if caption_edges else ""

        post = {
            "shortcode": node.get("shortcode"),
            "media_type": node.get("__typename"),
            "display_url": node.get("display_url"),
            "thumbnail_url": node.get("thumbnail_src"),
            "is_video": node.get("is_video", False),
            "likes": node.get("edge_liked_by", {}).get("count", 0),
            "comments": node.get("edge_media_to_comment", {}).get("count", 0),
            "caption": caption,
            "taken_at": node.get("taken_at_timestamp"),
            "pk": node.get("id"),
            "video_url": node.get("video_url"),
            "video_views": node.get("video_view_count"),
        }

        # Carousel (GraphSidecar)
        sidecar = node.get("edge_sidecar_to_children", {})
        if sidecar:
            children = []
            for child_edge in sidecar.get("edges", []):
                child = child_edge.get("node", {})
                children.append({
                    "pk": child.get("id"),
                    "shortcode": child.get("shortcode"),
                    "display_url": child.get("display_url"),
                    "is_video": child.get("is_video", False),
                    "video_url": child.get("video_url"),
                    "media_type": child.get("__typename"),
                    "display_resources": [
                        {"url": r.get("src"), "width": r.get("config_width"), "height": r.get("config_height")}
                        for r in child.get("display_resources", [])
                    ],
                })
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

    return {
        "pk": media.get("id"),
        "shortcode": media.get("shortcode"),
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
    raw_type = item.get("media_type", 1)

    result = {
        "pk": str(item.get("pk", "")),
        "id": item.get("id"),
        "shortcode": item.get("code"),
        "media_type": media_type_map.get(raw_type, f"type_{raw_type}"),
        "media_type_raw": raw_type,
        "display_url": image_url,
        "is_video": raw_type == 2,
        "likes": item.get("like_count", 0),
        "comments": item.get("comment_count", 0),
        "caption": caption_text,
        "taken_at": item.get("taken_at"),
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
