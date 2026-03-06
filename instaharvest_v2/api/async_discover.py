"""
Async Discover API
==================
Async version of DiscoverAPI. Full feature parity with sync version.

Provides:
    - get_suggested_users(user_id) -> List[UserShort]
    - get_suggested_users_raw(user_id) -> raw GraphQL response
    - chain(seed_user_id) -> Multi-layer lead discovery
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from ..async_client import AsyncHttpClient
from ..models.user import UserShort

logger = logging.getLogger("instaharvest_v2.discover")

# Verified doc_id for discover chaining (from browser, 2026-03)
# Must stay in sync with discover.py
DISCOVER_CHAINING_DOC_ID = "25814188068245954"


class AsyncDiscoverAPI:
    """
    Async Instagram Discover API — similar/suggested users.

    Corresponds to the "Suggested for you" section on profile pages.
    Returns similar accounts recommended by Instagram for a given user_id.

    Usage:
        ig = AsyncInstagram(...)
        users = await ig.discover.get_suggested_users(user_id=12345)
        for user in users:
            print(f"@{user.username} {'✓' if user.is_verified else ''}")
    """

    def __init__(self, client: AsyncHttpClient):
        self._client = client

    # ─── Raw API ────────────────────────────────────────────────

    async def get_suggested_users_raw(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Similar accounts — raw GraphQL response.

        Args:
            user_id: Target user ID
            doc_id: Custom doc_id

        Returns:
            Full GraphQL response dict
        """
        variables = {
            "module": "profile",
            "target_id": str(user_id),
        }
        payload = {
            "variables": json.dumps(variables),
            "doc_id": doc_id or DISCOVER_CHAINING_DOC_ID,
            "fb_api_caller_class": "RelayModern",
            "server_timestamps": "true",
            "fb_api_req_friendly_name": "PolarisProfileSuggestedUsersWithPreloadableQuery",
        }
        data = await self._client.post(
            "/graphql/query",
            data=payload,
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query",
        )
        return data

    # ─── Parsed API ─────────────────────────────────────────────

    async def get_suggested_users(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[UserShort]:
        """
        Similar accounts — parsed UserShort models.

        Returns ~80 similar accounts for a given user.

        Args:
            user_id: Target user ID (pk)
            doc_id: Custom doc_id

        Returns:
            List[UserShort]: List of suggested users
        """
        data = await self.get_suggested_users_raw(user_id=user_id, doc_id=doc_id)
        users_data = (
            data
            .get("data", {})
            .get("xdt_api__v1__discover__chaining", {})
            .get("users", [])
        )

        users: List[UserShort] = []
        for user_dict in users_data:
            if not isinstance(user_dict, dict):
                continue
            try:
                user = UserShort(
                    pk=user_dict.get("pk") or user_dict.get("id", 0),
                    username=user_dict.get("username", ""),
                    full_name=user_dict.get("full_name", ""),
                    is_verified=user_dict.get("is_verified", False),
                    is_private=user_dict.get("is_private", False),
                    profile_pic_url=user_dict.get("profile_pic_url", ""),
                )
                users.append(user)
            except Exception as e:
                logger.warning(f"Suggested user parse error: {e}")
                continue

        logger.info(f"Discover chaining: {len(users)} suggested for user_id={user_id}")
        return users

    # ─── Utility methods ────────────────────────────────────────

    async def get_verified_suggestions(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[UserShort]:
        """Returns only verified (blue badge) accounts."""
        all_users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u for u in all_users if u.is_verified]

    async def get_public_suggestions(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[UserShort]:
        """Returns only public (open profile) accounts."""
        all_users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u for u in all_users if not u.is_private]

    async def get_suggestion_usernames(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[str]:
        """Returns only a list of usernames."""
        users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u.username for u in users if u.username]

    async def explore(self) -> Dict[str, Any]:
        """Explore page content (proxy to /discover/topical_explore/)."""
        return await self._client.get(
            "/discover/topical_explore/",
            rate_category="get_default",
        )

    # ─── Chain Discovery (Async) ────────────────────────────────

    async def chain(
        self,
        seed_user_id: int | str,
        max_depth: int = 2,
        max_per_layer: int = 20,
        delay: float = 3.0,
        max_total: int = 10000,
        on_progress: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Async multi-layer chain discovery — thousands of leads from one seed.

        Args:
            seed_user_id: Starting user PK (numeric)
            max_depth: How many layers deep (1=single, 2=chain)
            max_per_layer: How many users to expand per layer
            delay: Seconds between API calls
            max_total: Safety limit for total unique users (memory guard)
            on_progress: Optional async/sync callback

        Returns:
            dict: {users, total_unique, layers, seed_id}

        Example:
            result = await ig.discover.chain(seed_user_id="1059031072")
            print(f"Found {result['total_unique']} unique accounts")
        """
        all_users: Dict[str, Dict[str, Any]] = {}
        layer_counts: Dict[int, int] = {}

        queue = [(str(seed_user_id), "__seed__", 0)]
        processed_ids: set = set()

        while queue:
            # Memory guard
            if len(all_users) >= max_total:
                logger.warning(f"Chain: max_total {max_total} reached, stopping.")
                break

            user_id, source, layer = queue.pop(0)

            if layer > max_depth:
                continue
            if user_id in processed_ids:
                continue
            processed_ids.add(user_id)

            # Per-layer limit
            if layer > 0:
                if layer not in layer_counts:
                    layer_counts[layer] = 0
                if layer_counts[layer] >= max_per_layer:
                    continue

            try:
                users = await self.get_suggested_users(user_id=user_id)

                new_count = 0
                for user in users:
                    username = user.username
                    if username and username not in all_users:
                        all_users[username] = {
                            "username": username,
                            "full_name": user.full_name,
                            "pk": user.pk,
                            "is_verified": user.is_verified,
                            "is_private": user.is_private,
                            "profile_pic_url": user.profile_pic_url,
                            "source": source if source != "__seed__" else "seed",
                            "layer": layer,
                        }
                        new_count += 1

                        if layer < max_depth and user.pk:
                            queue.append((str(user.pk), username, layer + 1))

                if layer > 0:
                    layer_counts[layer] = layer_counts.get(layer, 0) + 1

                if on_progress and source != "__seed__":
                    cb_result = on_progress(
                        layer, layer_counts.get(layer, 0), max_per_layer,
                        source if source != "__seed__" else "seed",
                        new_count, len(all_users),
                    )
                    if asyncio.iscoroutine(cb_result):
                        await cb_result

                await asyncio.sleep(delay)

            except Exception as e:
                logger.warning(f"Chain error for user_id={user_id}: {e}")
                if layer > 0:
                    layer_counts[layer] = layer_counts.get(layer, 0) + 1
                await asyncio.sleep(delay * 2)

        logger.info(
            f"Chain discovery complete: {len(all_users)} unique users "
            f"from seed={seed_user_id}, depth={max_depth}"
        )

        return {
            "users": list(all_users.values()),
            "total_unique": len(all_users),
            "layers": layer_counts,
            "seed_id": str(seed_user_id),
        }
