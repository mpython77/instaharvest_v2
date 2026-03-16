"""
GraphQL Feed Queries
====================
Feed/Timeline queries: timeline, liked, saved, tag feed, trending reels,
profile reels, profile tagged, location posts, highlights.
"""

import logging
from typing import Any, Dict, List, Optional

from .registries import DOC_IDS
from .transport import GraphQLTransport
from .parsers import GraphQLParsers

logger = logging.getLogger("instaharvest_v2")


class GraphQLFeeds(GraphQLTransport, GraphQLParsers):
    """Feed and timeline GraphQL query methods."""

    # ═══════════════════════════════════════════════════════════
    # FEED: Timeline (GraphQL doc_id)
    # ═══════════════════════════════════════════════════════════

    def get_timeline_v2(
        self,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Home timeline feed via modern GraphQL doc_id POST.
        Web-cookie compatible — no mobile session needed.

        Response structure: xdt_api__v1__feed__timeline__connection
        Edge types:
            - media: regular posts from followed accounts
            - explore_story: suggested/recommended posts
            - ad: sponsored content (filtered out)
            - suggested_users: people suggestions (filtered out)

        Args:
            count: Number of posts to fetch
            after: Pagination cursor (end_cursor from previous page)

        Returns:
            dict:
                - posts: List[dict] — parsed media items
                - has_next: bool — more pages available
                - end_cursor: str — cursor for next page
                - count: int — items in this page
                - raw_edge_types: dict — count of each edge type
        """
        variables = {
            "data": {
                "device_id": "web_client",
                "is_async_ads_double_request": "0",
                "is_async_ads_in_headload_enabled": "0",
                "is_async_ads_rti": "0",
                "rti_delivery_backend": "0",
            },
            "after": after,
            "before": None,
            "first": min(count, 12),
            "last": None,
            "variant": "home",
        }

        # Use root query for initial load, pagination query for scrolling
        if after:
            doc_id = DOC_IDS["feed_timeline_pagination"]
            friendly = "PolarisFeedRootPaginationCachedQuery_subscribe"
        else:
            doc_id = DOC_IDS["feed_timeline"]
            friendly = "PolarisFeedTimelineRootV2Query"

        data = self._graphql_doc_query(
            doc_id=doc_id,
            variables=variables,
            friendly_name=friendly,
        )

        return self._parse_timeline_connection(
            data, "xdt_api__v1__feed__timeline__connection"
        )

    def get_liked_v2(
        self,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Liked posts via modern GraphQL doc_id POST.
        Replaces legacy query_hash which no longer works.

        Args:
            count: Posts per page
            after: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        sess = self._client.get_session()
        user_id = str(sess.ds_user_id) if sess else ""

        variables = {
            "data": {"count": min(count, 50)},
            "id": user_id,
            "after": after,
            "before": None,
            "first": min(count, 50),
            "last": None,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["feed_liked"],
            variables=variables,
            friendly_name="PolarisLikedPostsQuery",
        )

        return self._parse_timeline_connection(
            data, "xdt_api__v1__feed__liked__connection"
        )

    def get_saved_v2(
        self,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saved/bookmarked posts via modern GraphQL doc_id POST.
        Replaces legacy query_hash.

        Args:
            count: Posts per page
            after: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        variables = {
            "collection_types": [
                "ALL_MEDIA_AUTO_COLLECTION",
                "MEDIA",
                "AUDIO_AUTO_COLLECTION",
            ],
            "count": min(count, 50),
            "get_cover_media_lists": True,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["feed_saved"],
            variables=variables,
            friendly_name="PolarisProfileSavedTabContentQuery",
        )

        # Saved returns collections list, parse accordingly
        conn_key = "xdt_api__v1__collections__list_graphql_connection"
        if isinstance(data, dict) and "data" in data:
            conn = data["data"].get(conn_key, {})
        elif isinstance(data, dict):
            conn = data.get(conn_key, {})
        else:
            conn = {}

        if not conn:
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

        edges = conn.get("edges", [])
        page_info = conn.get("page_info", {})

        # Extract collections with their media
        collections = []
        for edge in edges:
            node = edge.get("node", {})
            collections.append({
                "collection_id": node.get("collection_id"),
                "collection_name": node.get("collection_name"),
                "media_count": node.get("collection_media_count", 0),
                "cover_media_list": node.get("cover_media_list", []),
            })

        return {
            "posts": collections,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
            "count": len(collections),
        }

    def get_tag_feed_v2(
        self,
        hashtag: str,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Hashtag feed via modern GraphQL doc_id POST.
        Replaces REST /feed/tag/ which requires mobile session.

        Args:
            hashtag: Hashtag name (without #)
            count: Posts per page
            after: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        variables = {
            "data": {"count": min(count, 50), "include_relationship_info": True},
            "tag_name": hashtag.lstrip("#"),
            "after": after,
            "before": None,
            "first": min(count, 50),
            "last": None,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["feed_tag"],
            variables=variables,
            friendly_name="PolarisHashtagFeedQuery",
        )

        # Try known connection names for tag feed
        for conn_name in [
            "xdt_api__v1__feed__tag__connection",
            f"xdt_api__v1__feed__tag__{hashtag.lstrip('#')}__connection",
        ]:
            conn = data.get("data", {}).get(conn_name)
            if conn:
                return self._parse_timeline_connection_from_conn(conn)

        # Fallback: try first matching key
        data_root = data.get("data", {})
        for key, val in data_root.items():
            if "tag" in key and isinstance(val, dict) and "edges" in val:
                return self._parse_timeline_connection_from_conn(val)

        return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

    def get_reels_trending_v2(
        self,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trending reels via modern GraphQL doc_id POST.
        Replaces REST /clips/trending/ which requires mobile session.

        Args:
            count: Reels per page
            after: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        variables = {
            "data": {"count": min(count, 50)},
            "after": after,
            "before": None,
            "first": min(count, 50),
            "last": None,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["feed_reels_trending"],
            variables=variables,
            friendly_name="PolarisClipsTabDesktopPaginationQuery",
        )

        return self._parse_timeline_connection(
            data, "xdt_api__v1__clips__home__connection_v2"
        )

    # ═══════════════════════════════════════════════════════════
    # PROFILE REELS v2 — Reels tab with play_count/like_count
    # ═══════════════════════════════════════════════════════════

    def get_profile_reels_v2(
        self,
        user_id: str | int,
        page_size: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        User reels tab via modern doc_id (PolarisProfileReelsTabContentQuery).
        Returns rich data including play_count, like_count, comment_count.

        Args:
            user_id: Target user PK
            page_size: Reels per page (max 12)
            after: Pagination cursor (end_cursor from previous page)

        Returns:
            dict:
                - posts: list of reel dicts with play_count, like_count, etc.
                - has_next: bool
                - end_cursor: str
                - count: int
        """
        variables: Dict[str, Any] = {
            "data": {
                "include_feed_video": True,
                "page_size": page_size,
                "target_user_id": str(user_id),
            }
        }
        if after:
            variables["data"]["max_id"] = after

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["profile_reels_v2"],
            variables=variables,
            friendly_name="PolarisProfileReelsTabContentQuery",
        )

        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find the connection key
        conn = {}
        for key, val in raw_data.items():
            if isinstance(val, dict) and "edges" in val:
                conn = val
                break

        edges = conn.get("edges", [])
        page_info = conn.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            media = node.get("media", node)  # Sometimes nested under media
            if not isinstance(media, dict):
                continue

            user = media.get("user", {}) or {}
            caption_data = media.get("caption", {}) or {}
            caption_text = caption_data.get("text", "") if isinstance(caption_data, dict) else ""

            posts.append({
                "pk": media.get("pk"),
                "id": media.get("id"),
                "code": media.get("code", ""),
                "media_type": media.get("media_type", 2),
                "play_count": media.get("play_count", 0),
                "like_count": media.get("like_count", 0),
                "comment_count": media.get("comment_count", 0),
                "caption": caption_text,
                "taken_at": media.get("taken_at"),
                "video_duration": media.get("video_duration"),
                "thumbnail_url": (
                    media.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
                    if media.get("image_versions2") else ""
                ),
                "user": {
                    "pk": user.get("pk"),
                    "username": user.get("username", ""),
                },
            })

        return {
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
            "count": len(posts),
        }

    def get_all_profile_reels(
        self,
        user_id: str | int,
        max_count: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get ALL reels via auto-pagination.

        Args:
            user_id: User PK
            max_count: Maximum reels to fetch

        Returns:
            list: All reels with play_count, like_count, etc.
        """
        all_posts = []
        cursor = None

        while len(all_posts) < max_count:
            result = self.get_profile_reels_v2(
                user_id=user_id,
                page_size=12,
                after=cursor,
            )
            posts = result.get("posts", [])
            if not posts:
                break
            all_posts.extend(posts)
            if not result.get("has_next"):
                break
            cursor = result.get("end_cursor")
            if not cursor:
                break

        return all_posts[:max_count]

    # ═══════════════════════════════════════════════════════════
    # PROFILE TAGGED v2 — Tagged posts (new doc_id)
    # ═══════════════════════════════════════════════════════════

    def get_profile_tagged_v2(
        self,
        user_id: str | int,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tagged posts via modern doc_id (PolarisProfileTaggedTabContentQuery).
        Posts where the user is tagged by others.

        Args:
            user_id: Target user PK
            count: Posts per page (max 12)
            after: Pagination cursor

        Returns:
            dict:
                - posts: list of media dicts
                - has_next: bool
                - end_cursor: str
                - count: int
        """
        variables: Dict[str, Any] = {
            "count": count,
            "user_id": str(user_id),
        }
        if after:
            variables["after"] = after

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["profile_tagged_v2"],
            variables=variables,
            friendly_name="PolarisProfileTaggedTabContentQuery",
        )

        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find connection
        conn = {}
        for key, val in raw_data.items():
            if isinstance(val, dict) and "edges" in val:
                conn = val
                break

        edges = conn.get("edges", [])
        page_info = conn.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            if not isinstance(node, dict):
                continue

            user = node.get("user", {}) or {}
            caption_data = node.get("caption", {}) or {}
            caption_text = caption_data.get("text", "") if isinstance(caption_data, dict) else ""

            posts.append({
                "pk": node.get("pk"),
                "id": node.get("id"),
                "code": node.get("code", ""),
                "media_type": node.get("media_type", 1),
                "like_count": node.get("like_count", 0),
                "comment_count": node.get("comment_count", 0),
                "caption": caption_text,
                "taken_at": node.get("taken_at"),
                "carousel_media_count": node.get("carousel_media_count"),
                "thumbnail_url": (
                    node.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
                    if node.get("image_versions2") else
                    node.get("display_uri", "")
                ),
                "user": {
                    "pk": user.get("pk"),
                    "username": user.get("username", ""),
                    "full_name": user.get("full_name", ""),
                    "is_verified": user.get("is_verified", False),
                },
                "accessibility_caption": node.get("accessibility_caption"),
            })

        return {
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
            "count": len(posts),
        }

    def get_all_profile_tagged(
        self,
        user_id: str | int,
        max_count: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Get ALL tagged posts via auto-pagination.

        Args:
            user_id: User PK
            max_count: Maximum posts to fetch

        Returns:
            list: All tagged posts
        """
        all_posts = []
        cursor = None

        while len(all_posts) < max_count:
            result = self.get_profile_tagged_v2(
                user_id=user_id,
                count=12,
                after=cursor,
            )
            posts = result.get("posts", [])
            if not posts:
                break
            all_posts.extend(posts)
            if not result.get("has_next"):
                break
            cursor = result.get("end_cursor")
            if not cursor:
                break

        return all_posts[:max_count]

    # ═══════════════════════════════════════════════════════════
    # LOCATION POSTS — Posts by location (GraphQL)
    # ═══════════════════════════════════════════════════════════

    def get_location_posts(
        self,
        location_id: str | int,
        count: int = 12,
        tab: str = "ranked",
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Posts by location via GraphQL (PolarisLocationPageTabContentQuery).
        Better than REST — works with web cookies, no mobile session needed.

        Args:
            location_id: Location PK (e.g., "231385413" for Tashkent)
            count: Posts per page
            tab: "ranked" (top) or "recent"
            after: Pagination cursor

        Returns:
            dict:
                - posts: list of media dicts
                - has_next: bool
                - end_cursor: str
                - count: int
        """
        variables: Dict[str, Any] = {
            "first": count,
            "location_id": str(location_id),
            "page_size_override": min(count, 6),
            "tab": tab,
        }
        if after:
            variables["after"] = after

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["location_posts"],
            variables=variables,
            friendly_name="PolarisLocationPageTabContentQuery_connection",
        )

        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find connection
        conn = {}
        for key, val in raw_data.items():
            if isinstance(val, dict) and "edges" in val:
                conn = val
                break

        edges = conn.get("edges", [])
        page_info = conn.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            if not isinstance(node, dict):
                continue

            user = node.get("user", {}) or {}
            caption_data = node.get("caption", {}) or {}
            caption_text = caption_data.get("text", "") if isinstance(caption_data, dict) else ""
            location = node.get("location", {}) or {}

            posts.append({
                "pk": node.get("pk"),
                "id": node.get("id"),
                "code": node.get("code", ""),
                "media_type": node.get("media_type", 1),
                "like_count": node.get("like_count", 0),
                "comment_count": node.get("comment_count", 0),
                "play_count": node.get("play_count"),
                "caption": caption_text,
                "taken_at": node.get("taken_at"),
                "thumbnail_url": (
                    node.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
                    if node.get("image_versions2") else ""
                ),
                "user": {
                    "pk": user.get("pk"),
                    "username": user.get("username", ""),
                    "full_name": user.get("full_name", ""),
                    "is_verified": user.get("is_verified", False),
                },
                "location": {
                    "pk": location.get("pk"),
                    "name": location.get("name", ""),
                },
            })

        return {
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
            "count": len(posts),
        }

    def get_all_location_posts(
        self,
        location_id: str | int,
        max_count: int = 200,
        tab: str = "ranked",
    ) -> List[Dict[str, Any]]:
        """
        Get ALL location posts via auto-pagination.

        Args:
            location_id: Location PK
            max_count: Maximum posts to fetch
            tab: "ranked" or "recent"

        Returns:
            list: All posts at this location
        """
        all_posts = []
        cursor = None

        while len(all_posts) < max_count:
            result = self.get_location_posts(
                location_id=location_id,
                count=12,
                tab=tab,
                after=cursor,
            )
            posts = result.get("posts", [])
            if not posts:
                break
            all_posts.extend(posts)
            if not result.get("has_next"):
                break
            cursor = result.get("end_cursor")
            if not cursor:
                break

        return all_posts[:max_count]

    # ═══════════════════════════════════════════════════════════
    # HIGHLIGHTS ITEMS — Batch fetch highlight reel items
    # ═══════════════════════════════════════════════════════════

    def get_highlights_items(
        self,
        highlight_ids: List[str | int],
    ) -> Dict[str, Any]:
        """
        Batch fetch items from multiple highlight reels.
        Uses doc_id for web-compatible access (no mobile session needed).

        Args:
            highlight_ids: List of highlight reel IDs
                (e.g., ["highlight:17854360229135021", ...])

        Returns:
            dict:
                - highlights: list of highlight dicts, each with:
                    - id: str
                    - title: str
                    - items: list of story items
                    - cover_media: dict
                    - media_count: int
                - count: int
        """
        variables = {
            "highlight_reel_ids": [str(h) for h in highlight_ids],
            "precomposed_overlay": False,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["highlights_items"],
            variables=variables,
            friendly_name="PolarisProfileHighlightReelsQuery",
        )

        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find highlights in response — key varies
        reels_data = {}
        for key, val in raw_data.items():
            if isinstance(val, dict):
                reels_data = val
                break

        # Parse each highlight reel
        highlights = []
        # Could be dict of reels or list
        reels = reels_data.get("reels", reels_data)
        if isinstance(reels, dict):
            for reel_id, reel in reels.items():
                if not isinstance(reel, dict):
                    continue
                items = reel.get("items", [])
                highlights.append({
                    "id": reel.get("id", reel_id),
                    "title": reel.get("title", ""),
                    "media_count": reel.get("media_count", len(items)),
                    "cover_media": reel.get("cover_media", {}),
                    "created_at": reel.get("created_at"),
                    "items": [
                        {
                            "pk": item.get("pk"),
                            "id": item.get("id"),
                            "media_type": item.get("media_type", 1),
                            "taken_at": item.get("taken_at"),
                            "image_url": (
                                item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
                                if item.get("image_versions2") else ""
                            ),
                            "video_url": (
                                item.get("video_versions", [{}])[0].get("url", "")
                                if item.get("video_versions") else ""
                            ),
                            "video_duration": item.get("video_duration"),
                        }
                        for item in items
                        if isinstance(item, dict)
                    ],
                })
        elif isinstance(reels, list):
            for reel in reels:
                if not isinstance(reel, dict):
                    continue
                items = reel.get("items", [])
                highlights.append({
                    "id": reel.get("id"),
                    "title": reel.get("title", ""),
                    "media_count": reel.get("media_count", len(items)),
                    "cover_media": reel.get("cover_media", {}),
                    "created_at": reel.get("created_at"),
                    "items": [
                        {
                            "pk": item.get("pk"),
                            "id": item.get("id"),
                            "media_type": item.get("media_type", 1),
                            "taken_at": item.get("taken_at"),
                            "image_url": (
                                item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
                                if item.get("image_versions2") else ""
                            ),
                            "video_url": (
                                item.get("video_versions", [{}])[0].get("url", "")
                                if item.get("video_versions") else ""
                            ),
                            "video_duration": item.get("video_duration"),
                        }
                        for item in items
                        if isinstance(item, dict)
                    ],
                })

        return {
            "highlights": highlights,
            "count": len(highlights),
        }
