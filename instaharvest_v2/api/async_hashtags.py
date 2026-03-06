"""
Hashtags API
============
Hashtag info, posts, follow/unfollow, related.
Search with pagination — ig.hashtags.search_posts().
"""

from typing import Any, Dict, List, Optional

import asyncio
from ..async_client import AsyncHttpClient
from ..models.hashtag import HashtagSearchResult


class AsyncHashtagsAPI:
    """Instagram Hashtags API"""

    def __init__(self, client: AsyncHttpClient):
        self._client = client
        # SearchAPI ga reference — lazy init
        self._search_api = None

    async def _get_search_api(self):
        """Get lazy reference to AsyncSearchAPI."""
        if self._search_api is None:
            from .async_search import AsyncSearchAPI
            self._search_api = AsyncSearchAPI(self._client)
        return self._search_api

    # ─── SEARCH (PAGINATION) ────────────────────────────────

    async def search_posts(
        self,
        hashtag: str,
        max_pages: int = 1,
        next_max_id: Optional[str] = None,
        rank_token: Optional[str] = None,
        search_session_id: Optional[str] = None,
        delay: float = 2.0,
    ) -> HashtagSearchResult:
        """
        Search posts by hashtag — WITH PAGINATION.

        Shortcut method for SearchAPI.hashtag_search().

        Args:
            hashtag: Hashtag name ("#programmer" or "programmer")
            max_pages: How many pages to load (default 1)
            next_max_id: Cursor for continuation
            rank_token: Rank token (from previous result)
            search_session_id: Search session ID
            delay: Wait between pages (seconds)

        Returns:
            HashtagSearchResult: posts, users, pagination info

        Usage:
            result = ig.hashtags.search_posts("#fashion", max_pages=5)

            for post in result.posts:
                print(f"@{post.user.username}: {post.like_count} likes")

            # Continue
            if result.has_more:
                more = ig.hashtags.search_posts(
                    "#fashion",
                    next_max_id=result.next_max_id,
                    rank_token=result.rank_token,
                )
                result = result.merge(more)
        """
        api = await self._get_search_api()
        return await api.hashtag_search(
            hashtag=hashtag,
            max_pages=max_pages,
            next_max_id=next_max_id,
            rank_token=rank_token,
            search_session_id=search_session_id,
            delay=delay,
        )

    # ─── INFO ───────────────────────────────────────────────

    async def get_info(self, hashtag: str) -> Dict[str, Any]:
        """
        Hashtag info: how many posts, how many people follow.

        Args:
            hashtag: Hashtag name (without #)

        Returns:
            Hashtag data
        """
        return await self._client.get(
            f"/tags/{hashtag}/info/",
            rate_category="get_default",
        )

    async def get_posts(self, hashtag: str) -> Dict[str, Any]:
        """
        Hashtag posts (top + recent) — raw.

        Args:
            hashtag: Hashtag name

        Returns:
            Posts (in sections format)
        """
        return await self._client.post(
            f"/tags/{hashtag}/sections/",
            data={"tab": "top"},
            rate_category="get_feed",
        )

    # ─── FOLLOW / UNFOLLOW ──────────────────────────────────

    async def follow(self, hashtag: str) -> Dict[str, Any]:
        """
        Follow a hashtag.

        Args:
            hashtag: Hashtag name
        """
        return await self._client.post(
            f"/tags/follow/{hashtag}/",
            rate_category="post_follow",
        )

    async def unfollow(self, hashtag: str) -> Dict[str, Any]:
        """
        Unfollow a hashtag.

        Args:
            hashtag: Hashtag name
        """
        return await self._client.post(
            f"/tags/unfollow/{hashtag}/",
            rate_category="post_follow",
        )

    # ─── RELATED ────────────────────────────────────────────

    async def get_related(self, hashtag: str) -> List[Dict]:
        """
        Related hashtags.

        Args:
            hashtag: Hashtag name

        Returns:
            List of similar hashtags
        """
        data = await self._client.get(
            f"/tags/{hashtag}/related/",
            rate_category="get_default",
        )
        return data.get("related", [])
