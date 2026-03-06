"""
Feed API
========
User feeds: posts, liked, saved, timeline, tag, reels.
Pagination support. GraphQL v2 + REST fallback.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from ..client import HttpClient
from ..models.media import Media as MediaModel

logger = logging.getLogger("instaharvest_v2")


class FeedAPI:
    """Instagram feed API — GraphQL v2 with REST fallback."""

    def __init__(self, client: HttpClient, graphql=None):
        self._client = client
        self._graphql = graphql  # GraphQLAPI instance (injected)

    # ═══════════════════════════════════════════════════════════
    # USER FEED (REST — always works with session)
    # ═══════════════════════════════════════════════════════════

    def get_user_feed(
        self,
        user_id: int | str,
        count: int = 12,
        max_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        User posts.

        Args:
            user_id: User PK
            count: How many posts to get
            max_id: Pagination cursor (next page)

        Returns:
            Posts and pagination data
        """
        params = {"count": str(count)}
        if max_id:
            params["max_id"] = max_id

        data = self._client.get(
            f"/feed/user/{user_id}/",
            params=params,
            rate_category="get_feed",
        )
        return data

    def get_all_posts(
        self,
        user_id: int | str,
        max_posts: int = 100,
        count_per_page: int = 12,
        delay: float = 1.5,
    ) -> List[MediaModel]:
        """
        Get all posts (with pagination + anti-rate-limit delay).

        Args:
            user_id: User PK
            max_posts: Maximum number of posts
            count_per_page: Posts per page
            delay: Delay between pagination requests (seconds)

        Returns:
            List of Media models
        """
        all_posts = []
        max_id = None
        page = 0

        while len(all_posts) < max_posts:
            page += 1
            data = self.get_user_feed(user_id, count=count_per_page, max_id=max_id)

            items = data.get("items", [])
            all_posts.extend([MediaModel.from_api(item) for item in items])

            if not data.get("more_available"):
                break

            max_id = data.get("next_max_id")
            if not max_id:
                break

            if page > 1:
                time.sleep(delay)

        return all_posts[:max_posts]

    # ═══════════════════════════════════════════════════════════
    # TIMELINE (GraphQL v2 → REST fallback)
    # ═══════════════════════════════════════════════════════════

    def get_timeline(
        self,
        count: int = 12,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Home timeline feed.

        Strategy:
            1. GraphQL doc_id POST (web-cookie compatible)
            2. REST /feed/timeline/ (fallback, needs mobile session)

        Args:
            count: Number of posts
            cursor: Pagination cursor (end_cursor or max_id)

        Returns:
            dict: {posts, has_next, end_cursor, count, raw_edge_types}
        """
        # Strategy 1: GraphQL v2 (preferred)
        if self._graphql:
            try:
                return self._graphql.get_timeline_v2(count=count, after=cursor)
            except Exception as e:
                logger.debug(f"[Feed] GraphQL timeline failed: {e}, trying REST...")

        # Strategy 2: REST fallback
        try:
            params = {}
            if cursor:
                params["max_id"] = cursor
            data = self._client.get(
                "/feed/timeline/",
                params=params if params else None,
                rate_category="get_feed",
            )
            # Normalize REST response to v2 format
            items = data.get("items", [])
            return {
                "posts": items,
                "has_next": data.get("more_available", False),
                "end_cursor": data.get("next_max_id"),
                "count": len(items),
            }
        except Exception as e:
            logger.debug(f"[Feed] REST timeline also failed: {e}")
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

    def get_all_timeline(
        self,
        max_posts: int = 50,
        delay: float = 2.0,
    ) -> List[Dict]:
        """
        Get multiple pages of timeline (auto-pagination).

        Args:
            max_posts: Maximum posts to collect
            delay: Delay between pages (seconds)

        Returns:
            List of parsed post dicts
        """
        all_posts = []
        cursor = None
        page = 0

        while len(all_posts) < max_posts:
            page += 1
            result = self.get_timeline(count=12, cursor=cursor)
            all_posts.extend(result.get("posts", []))

            logger.debug(
                f"[Feed] Timeline page {page}: {result.get('count', 0)} posts "
                f"(total: {len(all_posts)})"
            )

            if not result.get("has_next") or not result.get("end_cursor"):
                break

            cursor = result["end_cursor"]
            time.sleep(delay)

        return all_posts[:max_posts]

    # ═══════════════════════════════════════════════════════════
    # LIKED POSTS (GraphQL v2 → legacy hash fallback)
    # ═══════════════════════════════════════════════════════════

    def get_liked(
        self,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        My liked posts.

        Strategy:
            1. GraphQL doc_id POST (modern, recommended)
            2. Legacy query_hash GET (deprecated, may not work)

        Args:
            count: Posts per page
            cursor: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        # Strategy 1: GraphQL v2
        if self._graphql:
            try:
                return self._graphql.get_liked_v2(count=count, after=cursor)
            except Exception as e:
                logger.debug(f"[Feed] GraphQL liked failed: {e}, trying legacy...")

        # Strategy 2: Legacy query_hash
        try:
            sess = self._client.get_session()
            variables = {"id": str(sess.ds_user_id) if sess else "", "first": count}
            if cursor:
                variables["after"] = cursor
            data = self._client.get(
                "/graphql/query/",
                params={
                    "query_hash": "d5d763b1e2acf209d62d22d184488e57",
                    "variables": json.dumps(variables),
                },
                rate_category="get_feed",
                full_url="https://www.instagram.com/graphql/query/",
            )
            return data
        except Exception as e:
            logger.debug(f"[Feed] Legacy liked also failed: {e}")
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

    # ═══════════════════════════════════════════════════════════
    # SAVED POSTS (GraphQL v2 → legacy hash fallback)
    # ═══════════════════════════════════════════════════════════

    def get_saved(
        self,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Saved (bookmarked) posts.

        Strategy:
            1. GraphQL doc_id POST (modern)
            2. Legacy query_hash GET (deprecated)

        Args:
            count: Posts per page
            cursor: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        # Strategy 1: GraphQL v2
        if self._graphql:
            try:
                return self._graphql.get_saved_v2(count=count, after=cursor)
            except Exception as e:
                logger.debug(f"[Feed] GraphQL saved failed: {e}, trying legacy...")

        # Strategy 2: Legacy query_hash
        try:
            sess = self._client.get_session()
            variables = {"id": str(sess.ds_user_id) if sess else "", "first": count}
            if cursor:
                variables["after"] = cursor
            data = self._client.get(
                "/graphql/query/",
                params={
                    "query_hash": "2ce1d673055b99c84dc0d5b62e3f30d2",
                    "variables": json.dumps(variables),
                },
                rate_category="get_feed",
                full_url="https://www.instagram.com/graphql/query/",
            )
            return data
        except Exception as e:
            logger.debug(f"[Feed] Legacy saved also failed: {e}")
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

    # ═══════════════════════════════════════════════════════════
    # TAG FEED (GraphQL v2 → REST fallback)
    # ═══════════════════════════════════════════════════════════

    def get_tag_feed(
        self,
        hashtag: str,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Posts feed by hashtag.

        Strategy:
            1. GraphQL doc_id POST (web-compatible)
            2. REST /feed/tag/ (needs mobile session)

        Args:
            hashtag: Hashtag name (without #)
            count: Posts per page
            cursor: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        # Strategy 1: GraphQL v2
        if self._graphql:
            try:
                return self._graphql.get_tag_feed_v2(
                    hashtag=hashtag, count=count, after=cursor
                )
            except Exception as e:
                logger.debug(f"[Feed] GraphQL tag feed failed: {e}, trying REST...")

        # Strategy 2: REST fallback
        try:
            params = {}
            if cursor:
                params["max_id"] = cursor
            return self._client.get(
                f"/feed/tag/{hashtag}/",
                params=params if params else None,
                rate_category="get_feed",
            )
        except Exception as e:
            logger.debug(f"[Feed] REST tag feed also failed: {e}")
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}

    # ═══════════════════════════════════════════════════════════
    # LOCATION FEED (REST only — no GraphQL equivalent yet)
    # ═══════════════════════════════════════════════════════════

    def get_location_feed(
        self,
        location_id: int | str,
        max_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Posts feed by location.

        Args:
            location_id: Location PK
            max_id: Pagination cursor

        Returns:
            dict: {items, more_available, next_max_id}
        """
        params = {}
        if max_id:
            params["max_id"] = max_id
        return self._client.get(
            f"/feed/location/{location_id}/",
            params=params if params else None,
            rate_category="get_feed",
        )

    # ═══════════════════════════════════════════════════════════
    # REELS FEED (GraphQL v2 → REST fallback)
    # ═══════════════════════════════════════════════════════════

    def get_reels_feed(
        self,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reels tab (trending reels).

        Strategy:
            1. GraphQL doc_id POST (web-compatible)
            2. REST /clips/trending/ (needs mobile session)

        Args:
            count: Reels per page
            cursor: Pagination cursor

        Returns:
            dict: {posts, has_next, end_cursor, count}
        """
        # Strategy 1: GraphQL v2
        if self._graphql:
            try:
                return self._graphql.get_reels_trending_v2(count=count, after=cursor)
            except Exception as e:
                logger.debug(f"[Feed] GraphQL reels failed: {e}, trying REST...")

        # Strategy 2: REST fallback
        try:
            params = {}
            if cursor:
                params["max_id"] = cursor
            return self._client.get(
                "/clips/trending/",
                params=params if params else None,
                rate_category="get_feed",
            )
        except Exception as e:
            logger.debug(f"[Feed] REST reels also failed: {e}")
            return {"posts": [], "has_next": False, "end_cursor": None, "count": 0}
