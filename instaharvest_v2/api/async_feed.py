"""
Feed API (Async)
================
User feeds: posts, liked, saved, timeline, tag, reels.
Pagination support. GraphQL v2 + REST fallback.
"""

import asyncio
from typing import Any, Dict, List, Optional

from ..async_client import AsyncHttpClient
from ..models.media import Media as MediaModel

import logging
logger = logging.getLogger("instaharvest_v2")


class AsyncFeedAPI:
    """Instagram feed API (async) — GraphQL v2 + REST fallback."""

    def __init__(self, client: AsyncHttpClient, graphql=None):
        self._client = client
        self._graphql = graphql  # AsyncGraphQLAPI instance (injected)

    async def get_user_feed(
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

        data = await self._client.get(
            f"/feed/user/{user_id}/",
            params=params,
            rate_category="get_feed",
        )
        return data

    async def get_all_posts(
        self,
        user_id: int | str,
        max_posts: int = 100,
        count_per_page: int = 12,
    ) -> List[MediaModel]:
        """
        Get all posts (with pagination).

        Args:
            user_id: User PK
            max_posts: Maximum number of posts
            count_per_page: Posts per page

        Returns:
            List of Media models
        """
        all_posts = []
        max_id = None

        while len(all_posts) < max_posts:
            data = await self.get_user_feed(user_id, count=count_per_page, max_id=max_id)

            items = data.get("items", [])
            all_posts.extend([MediaModel.from_api(item) for item in items])

            if not data.get("more_available"):
                break

            max_id = data.get("next_max_id")
            if not max_id:
                break

        return all_posts[:max_posts]

    async def get_liked(self, max_id: Optional[str] = None) -> Dict[str, Any]:
        """
        My liked posts.

        Args:
            max_id: Pagination cursor

        Returns:
            Liked posts
        """
        params = {}
        if max_id:
            params["max_id"] = max_id

        return await self._client.get(
            "/feed/liked/",
            params=params if params else None,
            rate_category="get_feed",
        )

    async def get_saved(self, max_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Saved (bookmarked) posts.

        Args:
            max_id: Pagination cursor

        Returns:
            Saved posts
        """
        params = {}
        if max_id:
            params["max_id"] = max_id

        return await self._client.get(
            "/feed/saved/",
            params=params if params else None,
            rate_category="get_feed",
        )

    # ─── TAG / LOCATION FEED ────────────────────────────────

    async def get_tag_feed(self, hashtag: str, max_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Posts feed by hashtag.

        Args:
            hashtag: Hashtag name (without #)
            max_id: Pagination cursor

        Returns:
            dict: {items, more_available, next_max_id}
        """
        params = {}
        if max_id:
            params["max_id"] = max_id
        return await self._client.get(
            f"/feed/tag/{hashtag}/",
            params=params if params else None,
            rate_category="get_feed",
        )

    async def get_location_feed(self, location_id: int | str, max_id: Optional[str] = None) -> Dict[str, Any]:
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
        return await self._client.get(
            f"/feed/location/{location_id}/",
            params=params if params else None,
            rate_category="get_feed",
        )

    # ─── TIMELINE (GraphQL v2 → REST fallback) ─────────────────

    async def get_timeline(self, max_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Home timeline feed — GraphQL v2 first, REST fallback.

        Args:
            max_id: Pagination cursor (end_cursor for GraphQL, max_id for REST)

        Returns:
            dict: {posts, count, has_next, end_cursor}
        """
        if self._graphql:
            try:
                return await self._graphql.get_timeline_v2(count=12, after=max_id)
            except Exception as e:
                logger.debug(f"GraphQL timeline failed, falling back to REST: {e}")

        # REST fallback
        params = {}
        if max_id:
            params["max_id"] = max_id
        return await self._client.get(
            "/feed/timeline/",
            params=params if params else None,
            rate_category="get_feed",
        )

    async def get_all_timeline(
        self,
        max_count: int = 50,
    ) -> Dict[str, Any]:
        """
        Get multiple pages of timeline (auto-pagination).

        Args:
            max_count: Maximum number of posts to get

        Returns:
            dict: {posts, count}
        """
        all_posts = []
        cursor = None

        while len(all_posts) < max_count:
            result = await self.get_timeline(max_id=cursor)

            posts = result.get("posts", result.get("feed_items", []))
            if not posts:
                break

            all_posts.extend(posts)
            cursor = result.get("end_cursor", result.get("next_max_id"))
            has_next = result.get("has_next", result.get("more_available", False))

            if not has_next or not cursor:
                break
            await asyncio.sleep(1.0)

        return {"posts": all_posts[:max_count], "count": len(all_posts[:max_count])}

    # ─── REELS (GraphQL v2 → REST fallback) ─────────────────

    async def get_reels_feed(self, max_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Reels tab — GraphQL v2 first, REST fallback.

        Args:
            max_id: Pagination cursor

        Returns:
            dict: Reels posts
        """
        if self._graphql:
            try:
                return await self._graphql.get_reels_trending_v2(count=10, after=max_id)
            except Exception as e:
                logger.debug(f"GraphQL reels failed, falling back to REST: {e}")

        params = {}
        if max_id:
            params["max_id"] = max_id
        return await self._client.get(
            "/clips/trending/",
            params=params if params else None,
            rate_category="get_feed",
        )

