"""
GraphQL Response Parsers
========================
Shared parsing logic for GraphQL connection responses, media nodes, etc.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("instaharvest_v2")


class GraphQLParsers:
    """Mixin providing response parsing methods."""

    def _parse_timeline_connection(
        self,
        data: Dict[str, Any],
        connection_key: str,
    ) -> Dict[str, Any]:
        """
        Parse GraphQL connection response with edges/page_info pattern.

        Handles:
            - edges[].node.media → regular posts
            - edges[].node.explore_story.media → suggested posts
            - edges[].node.ad → ads (skipped)
            - edges[].node.suggested_users → suggestions (skipped)

        Args:
            data: Raw GraphQL response
            connection_key: Key under data.data that contains the connection

        Returns:
            dict: {posts, has_next, end_cursor, count, raw_edge_types}
        """
        conn = data.get("data", {}).get(connection_key, {})
        return self._parse_timeline_connection_from_conn(conn)

    def _parse_timeline_connection_from_conn(
        self,
        conn: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Parse from an already-extracted connection dict.
        """
        if not conn:
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

        edges = conn.get("edges", [])
        page_info = conn.get("page_info", {})

        posts = []
        edge_types = {"media": 0, "explore": 0, "ad": 0, "suggested": 0, "other": 0}

        for edge in edges:
            node = edge.get("node", {})
            media = None
            source = "feed"

            # Priority 1: direct media
            if node.get("media"):
                media = node["media"]
                edge_types["media"] += 1
                source = "feed"

            # Priority 2: explore_story (suggested content)
            elif node.get("explore_story"):
                explore_media = node["explore_story"].get("media")
                if explore_media:
                    media = explore_media
                    edge_types["explore"] += 1
                    source = "explore"

            # Skip: ads
            elif node.get("ad"):
                edge_types["ad"] += 1
                continue

            # Skip: suggested users
            elif node.get("suggested_users"):
                edge_types["suggested"] += 1
                continue

            # Skip: unknown types
            else:
                edge_types["other"] += 1
                continue

            if media:
                parsed = self._parse_v2_media(media)
                parsed["feed_source"] = source
                explore_info = (node.get("explore_story", {}) or {}).get("media", {})
                if source == "explore" and explore_info:
                    explore_meta = explore_info.get("explore", {})
                    if explore_meta:
                        parsed["explore_title"] = explore_meta.get("title", "")
                posts.append(parsed)

        return {
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
            "count": len(posts),
            "raw_edge_types": edge_types,
        }

    # ═══════════════════════════════════════════════════════════
    # HELPER: Parse v2 media node
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _parse_v2_media(node: Dict) -> Dict[str, Any]:
        """
        Parse a v2 (REST-like) media node from GraphQL response.
        Extracts ALL available data into a clean dict.

        Args:
            node: Raw media node from GraphQL

        Returns:
            dict: Structured media info
        """
        user = node.get("user", {}) or {}
        caption_data = node.get("caption", {}) or {}
        location = node.get("location", {}) or {}
        music = node.get("music_metadata", {}) or {}
        music_info = music.get("music_info", {}) or {}
        music_asset = music_info.get("music_asset_info", {}) or {}
        clips_meta = node.get("clips_metadata", {}) or {}

        # Image versions
        images = []
        for img in (node.get("image_versions2", {}) or {}).get("candidates", []):
            images.append({
                "width": img.get("width"),
                "height": img.get("height"),
                "url": img.get("url", ""),
            })

        # Video versions
        videos = []
        for vid in (node.get("video_versions", []) or []):
            videos.append({
                "width": vid.get("width"),
                "height": vid.get("height"),
                "url": vid.get("url", ""),
                "type": vid.get("type"),
            })

        # Carousel items
        carousel = []
        for item in (node.get("carousel_media", []) or []):
            carousel.append({
                "pk": item.get("pk"),
                "media_type": item.get("media_type"),
                "images": [
                    {"width": c.get("width"), "height": c.get("height"), "url": c.get("url")}
                    for c in (item.get("image_versions2", {}) or {}).get("candidates", [])
                ],
                "videos": [
                    {"width": v.get("width"), "height": v.get("height"), "url": v.get("url")}
                    for v in (item.get("video_versions", []) or [])
                ],
                "tagged_users": [
                    {
                        "username": (t.get("user", {}) or {}).get("username"),
                        "pk": (t.get("user", {}) or {}).get("pk"),
                        "position": t.get("position"),
                    }
                    for t in (item.get("usertags", {}) or {}).get("in", [])
                ],
            })

        # Tagged users
        tagged_users = []
        for tag in (node.get("usertags", {}) or {}).get("in", []):
            tag_user = tag.get("user", {}) or {}
            tagged_users.append({
                "username": tag_user.get("username"),
                "pk": tag_user.get("pk"),
                "full_name": tag_user.get("full_name", ""),
                "is_verified": tag_user.get("is_verified", False),
                "position": tag.get("position"),
            })

        # Top likers (facepile)
        top_likers = [
            u.get("username", "")
            for u in (node.get("facepile_top_likers", []) or [])
        ]

        # Coauthors
        coauthors = [
            {
                "pk": co.get("pk"),
                "username": co.get("username"),
                "full_name": co.get("full_name", ""),
                "is_verified": co.get("is_verified", False),
            }
            for co in (node.get("coauthor_producers", []) or [])
        ]

        media_type_int = node.get("media_type", 0)
        media_type_name = {1: "photo", 2: "video", 8: "carousel"}.get(media_type_int, str(media_type_int))

        return {
            # Identity
            "pk": node.get("pk"),
            "id": node.get("id", ""),
            "code": node.get("code", ""),
            "shortcode": node.get("code", ""),

            # Type
            "media_type": media_type_int,
            "media_type_name": media_type_name,
            "is_photo": media_type_int == 1,
            "is_video": media_type_int == 2,
            "is_carousel": media_type_int == 8,
            "is_reel": bool(clips_meta),
            "product_type": node.get("product_type", ""),

            # Engagement
            "like_count": node.get("like_count", 0),
            "comment_count": node.get("comment_count", 0),
            "play_count": node.get("play_count"),
            "view_count": node.get("view_count"),
            "reshare_count": node.get("reshare_count"),
            "fb_play_count": node.get("fb_play_count"),
            "top_likers": top_likers,

            # Caption
            "caption": caption_data.get("text", "") if isinstance(caption_data, dict) else "",
            "caption_created_at": caption_data.get("created_at") if isinstance(caption_data, dict) else None,

            # Owner
            "user": {
                "pk": user.get("pk"),
                "username": user.get("username", ""),
                "full_name": user.get("full_name", ""),
                "is_verified": user.get("is_verified", False),
                "is_private": user.get("is_private", False),
                "profile_pic_url": user.get("profile_pic_url", ""),
            },
            "coauthors": coauthors,

            # Timestamps
            "taken_at": node.get("taken_at"),
            "device_timestamp": node.get("device_timestamp"),

            # Media
            "images": images,
            "videos": videos,
            "carousel": carousel,
            "carousel_media_count": node.get("carousel_media_count"),
            "original_width": node.get("original_width"),
            "original_height": node.get("original_height"),
            "video_duration": node.get("video_duration"),

            # Location
            "location": {
                "pk": location.get("pk"),
                "name": location.get("name", ""),
                "address": location.get("address", ""),
                "city": location.get("city", ""),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "short_name": location.get("short_name", ""),
            } if location else None,

            # Tagged
            "tagged_users": tagged_users,

            # Music
            "music": {
                "title": music_asset.get("title", ""),
                "artist": music_asset.get("display_artist", ""),
                "duration_ms": music_asset.get("duration_in_ms"),
                "id": music_asset.get("audio_asset_id"),
            } if music_asset else None,

            # Flags
            "comments_disabled": node.get("comments_disabled", False),
            "commenting_disabled_for_viewer": node.get("commenting_disabled_for_viewer", False),
            "like_and_view_counts_disabled": node.get("like_and_view_counts_disabled", False),
            "has_liked": node.get("has_liked", False),
            "has_saved": node.get("has_viewer_saved", False),
            "is_paid_partnership": node.get("is_paid_partnership", False),
            "is_organic_product_tagging_eligible": node.get("is_organic_product_tagging_eligible", False),
        }
