"""
Discover API
============
Instagram Discover / Suggested Users endpoint.

Endpoint:
    POST /graphql/query  (doc_id based)
    Response key: data.xdt_api__v1__discover__chaining.users[]

Provides:
    - get_suggested_users(user_id) -> List[UserShort]
    - get_suggested_users_raw(user_id) -> raw GraphQL response
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

import asyncio
from ..async_client import AsyncHttpClient
from ..models.user import UserShort

logger = logging.getLogger("instaharvest_v2.discover")

# Verified doc_id for discover chaining (from browser, 2026-03)
# Used by Instagram web client for "Suggested for you" on profile pages
DISCOVER_CHAINING_DOC_ID = "25814188068245954"


class AsyncDiscoverAPI:
    """
    Instagram Discover API — similar/suggested users.

    Corresponds to the "Suggested for you" section on profile pages. 
    Returns similar accounts recommended by Instagram for a given user_id.

    Usage:
        ig = Instagram.from_env()
        
        # As UserShort models
        users = ig.discover.get_suggested_users(user_id=12345)
        for user in users:
            print(f"@{user.username} - {user.full_name} {'✓' if user.is_verified else ''}")
        
        # Raw response
        data = ig.discover.get_suggested_users_raw(user_id=12345)
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
            user_id: Target user ID (profile owner PK)
            doc_id: Custom doc_id (if default doesn't work)

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

        Corresponds to "Suggested for you" on Instagram profile pages.
        Returns ~30 similar accounts for a given user.

        Args:
            user_id: Target user ID (pk)
            doc_id: Custom doc_id (if default doesn't work)

        Returns:
            List[UserShort]: List of suggested users
                Each UserShort: pk, username, full_name, is_verified, is_private, profile_pic_url

        Example:
            users = ig.discover.get_suggested_users(12345)
            verified = [u for u in users if u.is_verified]
            print(f"{len(verified)} verified from {len(users)} suggestions")
        """
        data = await self.get_suggested_users_raw(user_id=user_id, doc_id=doc_id)

        # Response structure: data.xdt_api__v1__discover__chaining.users[]
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

        logger.info(
            f"Discover chaining: {len(users)} suggested users for user_id={user_id}"
        )
        return users

    # ─── Utility methods ────────────────────────────────────────

    async def get_verified_suggestions(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[UserShort]:
        """
        Returns only verified (blue badge) accounts.

        Args:
            user_id: Target user ID

        Returns:
            List[UserShort]: Only verified users
        """
        all_users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u for u in all_users if u.is_verified]

    async def get_public_suggestions(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[UserShort]:
        """
        Returns only public (open profile) accounts.

        Args:
            user_id: Target user ID

        Returns:
            List[UserShort]: Only public users
        """
        all_users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u for u in all_users if not u.is_private]

    async def get_suggestion_usernames(
        self,
        user_id: int | str,
        doc_id: Optional[str] = None,
    ) -> List[str]:
        """
        Returns only a list of usernames.

        Args:
            user_id: Target user ID

        Returns:
            List[str]: List of usernames
        """
        users = await self.get_suggested_users(user_id=user_id, doc_id=doc_id)
        return [u.username for u in users if u.username]

    async def explore(self) -> Dict[str, Any]:
        """
        Explore page content (proxy to /discover/topical_explore/).

        Returns:
            Explore posts and clusters
        """
        return await self._client.get(
            "/discover/topical_explore/",
            rate_category="get_default",
        )

    # ─── Chain Discovery ────────────────────────────────────────

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
        Multi-layer chain discovery — thousands of leads from one seed.

        Starts from a seed user and recursively discovers suggested accounts.
        Each suggested user yields ~80 more similar accounts.

        Architecture:
            Layer 0: seed_user_id (1 user)
            Layer 1: get_suggested_users(seed) → ~80 users
            Layer 2: get_suggested_users(each layer1) → ~80 × max_per_layer users
            ...

        Args:
            seed_user_id: Starting user PK (numeric)
            max_depth: How many layers deep (1=single, 2=chain, 3=deep chain)
            max_per_layer: How many users to expand per layer (limits API calls)
            delay: Seconds between API calls (rate limiting)
            on_progress: Optional callback fn(layer, index, total, username, new_count, total_unique)

        Returns:
            dict:
                - users: list of user dicts (username, pk, full_name, ...)
                - total_unique: int — total unique accounts found
                - layers: dict — count per layer
                - seed_id: str

        Example:
            # Simple — one seed, 2 layers
            result = ig.discover.chain(seed_user_id="1059031072")
            print(f"Found {result['total_unique']} unique accounts")

            # With progress callback
            async def progress(layer, i, total, username, new, unique):
                print(f"[L{layer}] {i}/{total} @{username} +{new} (total: {unique})")

            result = ig.discover.chain(
                seed_user_id="1059031072",
                max_depth=2,
                max_per_layer=30,
                on_progress=progress,
            )

            # Save to CSV
            import csv
            with open("leads.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["username", "full_name", "pk"])
                w.writeheader()
                w.writerows(result["users"])
        """
        import time as _time

        all_users: Dict[str, Dict[str, Any]] = {}  # username -> data
        layer_counts: Dict[int, int] = {}

        # Queue: list of (user_id, source_username, layer)
        queue = [(str(seed_user_id), "__seed__", 0)]
        processed_ids = set()

        current_layer = 0
        while queue:
            # Memory guard
            if len(all_users) >= max_total:
                logger.warning(f"Chain: max_total {max_total} reached, stopping.")
                break

            user_id, source, layer = queue.pop(0)

            # Layer depth check
            if layer > max_depth:
                continue

            # Already processed this user_id
            if user_id in processed_ids:
                continue
            processed_ids.add(user_id)

            # New layer started?
            if layer > current_layer:
                current_layer = layer

            # Per-layer expansion limit
            layer_expanded = sum(
                1 for uid in processed_ids
                if uid != str(seed_user_id)
            )

            # For non-seed layers, limit how many we expand
            if layer > 0:
                layer_items = [
                    (uid, src, lyr)
                    for uid, src, lyr in [(user_id, source, layer)]
                ]
                # Count how many from this layer we've expanded
                if layer not in layer_counts:
                    layer_counts[layer] = 0
                if layer_counts[layer] >= max_per_layer:
                    continue

            try:
                users = await self.get_suggested_users(
                    user_id=user_id
                )

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

                        # Add to queue for next layer expansion
                        if layer < max_depth and user.pk:
                            queue.append((str(user.pk), username, layer + 1))

                if layer > 0:
                    layer_counts[layer] = layer_counts.get(layer, 0) + 1

                # Progress callback
                if on_progress and source != "__seed__":
                    on_progress(
                        layer,
                        layer_counts.get(layer, 0),
                        max_per_layer,
                        source if source != "__seed__" else "seed",
                        new_count,
                        len(all_users),
                    )
                elif source == "__seed__":
                    logger.info(
                        f"Chain L0: {len(users)} suggested from seed. "
                        f"New: {new_count}, Total: {len(all_users)}"
                    )

                _time.sleep(delay)

            except Exception as e:
                logger.warning(f"Chain error for user_id={user_id}: {e}")
                if layer > 0:
                    layer_counts[layer] = layer_counts.get(layer, 0) + 1
                _time.sleep(delay * 2)

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
