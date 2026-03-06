"""
GraphQL API (Async)
===================
Fetch data via Instagram GraphQL API — async version.
Supports both legacy query_hash (GET) and modern doc_id (POST).
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from ..async_client import AsyncHttpClient
from .graphql import DOC_IDS, QUERY_HASHES, GraphQLAPI

logger = logging.getLogger("instaharvest_v2")


class AsyncGraphQLAPI:
    """
    Instagram GraphQL query API (async).

    Supports both legacy query_hash (GET) and modern doc_id (POST).
    """

    def __init__(self, client: AsyncHttpClient):
        self._client = client

    # ═══════════════════════════════════════════════════════════
    # TRANSPORT: query_hash GET (legacy)
    # ═══════════════════════════════════════════════════════════

    async def _graphql_query(
        self,
        query_hash: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send GraphQL query (GET /graphql/query/).
        """
        data = await self._client.get(
            "/graphql/query/",
            params={
                "query_hash": query_hash,
                "variables": json.dumps(variables),
            },
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query/",
        )
        return data

    # ═══════════════════════════════════════════════════════════
    # TRANSPORT: doc_id POST (modern, 2024+)
    # ═══════════════════════════════════════════════════════════

    async def _graphql_doc_query(
        self,
        doc_id: str,
        variables: Dict[str, Any],
        friendly_name: str = "",
    ) -> Dict[str, Any]:
        """
        Send GraphQL query via doc_id (POST /graphql/query).
        """
        payload = {
            "variables": json.dumps(variables),
            "doc_id": doc_id,
            "fb_api_caller_class": "RelayModern",
            "server_timestamps": "true",
        }
        if friendly_name:
            payload["fb_api_req_friendly_name"] = friendly_name

        data = await self._client.post(
            "/graphql/query",
            data=payload,
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query",
        )
        return data

    # ═══════════════════════════════════════════════════════════
    # FOLLOWERS / FOLLOWING
    # ═══════════════════════════════════════════════════════════

    async def get_followers(
        self,
        user_id: str | int,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get followers via GraphQL (with pagination)."""
        variables = {
            "id": str(user_id),
            "include_reel": True,
            "fetch_mutual": True,
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = await self._graphql_query(QUERY_HASHES["followers"], variables)

        edge = data.get("data", {}).get("user", {}).get("edge_followed_by", {})
        page_info = edge.get("page_info", {})
        users = []
        for e in edge.get("edges", []):
            node = e.get("node", {})
            users.append({
                "pk": node.get("id"),
                "username": node.get("username"),
                "full_name": node.get("full_name"),
                "is_verified": node.get("is_verified"),
                "is_private": node.get("is_private"),
                "profile_pic_url": node.get("profile_pic_url"),
                "followed_by_viewer": node.get("followed_by_viewer"),
                "follows_viewer": node.get("follows_viewer"),
                "requested_by_viewer": node.get("requested_by_viewer"),
                "has_reel": bool(node.get("reel")),
            })

        return {
            "count": edge.get("count", 0),
            "users": users,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    async def get_all_followers(
        self,
        user_id: str | int,
        max_count: int = 5000,
    ) -> List[Dict]:
        """Get ALL followers (auto-pagination)."""
        all_users = []
        cursor = None
        while len(all_users) < max_count:
            result = await self.get_followers(user_id, count=50, after=cursor)
            all_users.extend(result["users"])
            if not result["has_next"] or not result["end_cursor"]:
                break
            cursor = result["end_cursor"]
        return all_users[:max_count]

    async def get_following(
        self,
        user_id: str | int,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get following via GraphQL (with pagination)."""
        variables = {
            "id": str(user_id),
            "include_reel": True,
            "fetch_mutual": True,
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = await self._graphql_query(QUERY_HASHES["following"], variables)

        edge = data.get("data", {}).get("user", {}).get("edge_follow", {})
        page_info = edge.get("page_info", {})
        users = []
        for e in edge.get("edges", []):
            node = e.get("node", {})
            users.append({
                "pk": node.get("id"),
                "username": node.get("username"),
                "full_name": node.get("full_name"),
                "is_verified": node.get("is_verified"),
                "is_private": node.get("is_private"),
                "profile_pic_url": node.get("profile_pic_url"),
                "followed_by_viewer": node.get("followed_by_viewer"),
                "follows_viewer": node.get("follows_viewer"),
                "requested_by_viewer": node.get("requested_by_viewer"),
            })

        return {
            "count": edge.get("count", 0),
            "users": users,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    async def get_all_following(
        self,
        user_id: str | int,
        max_count: int = 5000,
    ) -> List[Dict]:
        """Get ALL followings (auto-pagination)."""
        all_users = []
        cursor = None
        while len(all_users) < max_count:
            result = await self.get_following(user_id, count=50, after=cursor)
            all_users.extend(result["users"])
            if not result["has_next"] or not result["end_cursor"]:
                break
            cursor = result["end_cursor"]
        return all_users[:max_count]

    # ═══════════════════════════════════════════════════════════
    # POSTS (legacy)
    # ═══════════════════════════════════════════════════════════

    async def get_user_posts(
        self,
        user_id: str | int,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get posts via GraphQL (legacy query_hash)."""
        variables = {
            "id": str(user_id),
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = await self._graphql_query(QUERY_HASHES["user_posts"], variables)

        edge = data.get("data", {}).get("user", {}).get(
            "edge_owner_to_timeline_media", {}
        )
        page_info = edge.get("page_info", {})
        posts = []
        for e in edge.get("edges", []):
            node = e.get("node", {})
            caption_edge = node.get("edge_media_to_caption", {})
            caption_text = ""
            if caption_edge.get("edges"):
                caption_text = caption_edge["edges"][0].get("node", {}).get("text", "")

            posts.append({
                "pk": node.get("id"),
                "shortcode": node.get("shortcode"),
                "media_type": node.get("__typename"),
                "display_url": node.get("display_url"),
                "thumbnail_url": node.get("thumbnail_src"),
                "is_video": node.get("is_video", False),
                "video_view_count": node.get("video_view_count"),
                "likes": node.get("edge_liked_by", {}).get("count", 0),
                "comments": node.get("edge_media_to_comment", {}).get("count", 0),
                "caption": caption_text,
                "taken_at": node.get("taken_at_timestamp"),
                "dimensions": node.get("dimensions"),
                "location": node.get("location"),
                "accessibility_caption": node.get("accessibility_caption"),
            })

        return {
            "count": edge.get("count", 0),
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    # ═══════════════════════════════════════════════════════════
    # POSTS v2 (modern doc_id POST)
    # ═══════════════════════════════════════════════════════════

    async def get_user_posts_v2(
        self,
        username: str,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """User posts via modern doc_id POST."""
        variables = {
            "data": {
                "count": min(count, 50),
                "include_relationship_info": True,
                "latest_besties_reel_media": True,
                "latest_reel_media": True,
            },
            "username": username,
            "first": min(count, 50),
            "after": after,
            "before": None,
            "last": None,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["profile_posts"],
            variables=variables,
            friendly_name="PolarisProfilePostsTabContentQuery_connection",
        )

        connection = (
            data.get("data", {})
            .get("xdt_api__v1__feed__user_timeline_graphql_connection", {})
        )

        edges = connection.get("edges", [])
        page_info = connection.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            posts.append(GraphQLAPI._parse_v2_media(node))

        return {
            "posts": posts,
            "count": len(posts),
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    async def get_all_user_posts_v2(
        self,
        username: str,
        max_count: int = 100,
    ) -> List[Dict]:
        """Get ALL posts via doc_id (auto-pagination)."""
        all_posts = []
        cursor = None
        page = 0

        while len(all_posts) < max_count:
            page += 1
            batch = min(12, max_count - len(all_posts))

            result = await self.get_user_posts_v2(
                username, count=batch, after=cursor,
            )

            all_posts.extend(result["posts"])
            logger.debug(f"[GraphQL] Page {page}: got {len(result['posts'])} posts (total: {len(all_posts)})")

            if not result["has_next"] or not result["end_cursor"]:
                break

            cursor = result["end_cursor"]
            await asyncio.sleep(0.5)

        return all_posts[:max_count]

    # ═══════════════════════════════════════════════════════════
    # MEDIA DETAIL / COMMENTS / LIKERS (via doc_id)
    # ═══════════════════════════════════════════════════════════

    async def get_media_detail(self, shortcode: str) -> Dict[str, Any]:
        """Full media detail via doc_id POST."""
        variables = {
            "shortcode": shortcode,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["media_detail"],
            variables=variables,
            friendly_name="PolarisPostActionLoadPostQueryQuery",
        )

        item = data.get("data", {}).get("xdt_shortcode_media", {})
        if item:
            return GraphQLAPI._parse_v2_media(item)
        return data

    async def get_comments_v2(
        self,
        media_id: str | int,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post comments via doc_id POST."""
        variables = {
            "media_id": str(media_id),
            "first": min(count, 50),
            "last": None,
            "after": after,
            "before": None,
            "sort_order": "popular",
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["media_comments"],
            variables=variables,
            friendly_name="PolarisPostCommentsPaginationQuery",
        )

        connection = (
            data.get("data", {})
            .get("xdt_api__v1__media__media_id__comments__connection", {})
        )

        edges = connection.get("edges", [])
        page_info = connection.get("page_info", {})

        comments = []
        for edge in edges:
            node = edge.get("node", {})
            user = node.get("user", {})
            comments.append({
                "pk": node.get("pk"),
                "text": node.get("text", ""),
                "created_at": node.get("created_at"),
                "like_count": node.get("comment_like_count", 0),
                "user": {
                    "pk": user.get("pk"),
                    "username": user.get("username"),
                    "full_name": user.get("full_name", ""),
                    "is_verified": user.get("is_verified", False),
                    "profile_pic_url": user.get("profile_pic_url", ""),
                },
                "child_comment_count": node.get("child_comment_count", 0),
                "has_replies": node.get("child_comment_count", 0) > 0,
                "preview_replies": [
                    {
                        "pk": r.get("pk"),
                        "text": r.get("text", ""),
                        "user": r.get("user", {}),
                        "created_at": r.get("created_at"),
                    }
                    for r in (node.get("preview_child_comments", []) or [])
                ],
                "is_liked": node.get("has_liked_comment", False),
            })

        return {
            "comments": comments,
            "count": len(comments),
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    async def get_likers_v2(
        self,
        shortcode: str,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post likers via doc_id POST."""
        variables = {
            "shortcode": shortcode,
            "first": min(count, 50),
            "after": after,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["media_likers"],
            variables=variables,
            friendly_name="LikesQuery",
        )

        connection = (
            data.get("data", {})
            .get("xdt_shortcode_media", {})
            .get("edge_liked_by", {})
        )

        edges = connection.get("edges", [])
        page_info = connection.get("page_info", {})

        users = []
        for edge in edges:
            node = edge.get("node", {})
            users.append({
                "pk": node.get("id"),
                "username": node.get("username"),
                "full_name": node.get("full_name", ""),
                "is_verified": node.get("is_verified", False),
                "profile_pic_url": node.get("profile_pic_url", ""),
                "followed_by_viewer": node.get("followed_by_viewer", False),
            })

        return {
            "users": users,
            "count": connection.get("count", len(users)),
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    # ═══════════════════════════════════════════════════════════
    # TAGGED POSTS (legacy)
    # ═══════════════════════════════════════════════════════════

    async def get_tagged_posts(
        self,
        user_id: str | int,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """User tagged posts (tagged/photos of you)."""
        variables = {
            "id": str(user_id),
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = await self._graphql_query(QUERY_HASHES["tagged_posts"], variables)

        edge = data.get("data", {}).get("user", {}).get(
            "edge_user_to_photos_of_you", {}
        )
        page_info = edge.get("page_info", {})
        posts = []
        for e in edge.get("edges", []):
            node = e.get("node", {})
            owner = node.get("owner", {})
            caption_edge = node.get("edge_media_to_caption", {})
            caption_text = ""
            if caption_edge.get("edges"):
                caption_text = caption_edge["edges"][0].get("node", {}).get("text", "")

            posts.append({
                "pk": node.get("id"),
                "shortcode": node.get("shortcode"),
                "media_type": node.get("__typename"),
                "display_url": node.get("display_url"),
                "is_video": node.get("is_video", False),
                "likes": node.get("edge_liked_by", {}).get("count", 0),
                "comments": node.get("edge_media_to_comment", {}).get("count", 0),
                "caption": caption_text,
                "taken_at": node.get("taken_at_timestamp"),
                "owner_username": owner.get("username"),
                "owner_id": owner.get("id"),
            })

        return {
            "count": edge.get("count", 0),
            "posts": posts,
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    # ═══════════════════════════════════════════════════════════
    # HOVER CARD / SUGGESTED / LIKE / TIMELINE / REELS / SAVED
    # ═══════════════════════════════════════════════════════════

    async def get_hover_card(
        self,
        user_id: str,
        username: str,
    ) -> Dict[str, Any]:
        """Mini profile popup — fast user info."""
        variables = {"userID": str(user_id), "username": username}

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["profile_hover_card"],
            variables=variables,
            friendly_name="PolarisUserHoverCardContentV2Query",
        )

        info = data.get("data", {}).get("xdt_api__v1__users__info", {})
        friendship = info.get("friendship_status", {}) or {}
        mutual = info.get("mutual_followers", {}) or {}

        return {
            "pk": info.get("pk"),
            "username": info.get("username", username),
            "full_name": info.get("full_name", ""),
            "biography": info.get("biography", ""),
            "follower_count": info.get("follower_count", 0),
            "following_count": info.get("following_count", 0),
            "media_count": info.get("media_count", 0),
            "is_verified": info.get("is_verified", False),
            "is_private": info.get("is_private", False),
            "profile_pic_url": info.get("profile_pic_url", ""),
            "is_following": friendship.get("following", False),
            "is_followed_by": friendship.get("followed_by", False),
            "mutual_count": mutual.get("count", 0),
            "mutual_followers": mutual.get("users", []),
        }

    async def get_suggested_users(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Similar accounts for a user (Suggested for you)."""
        variables = {"module": "profile", "target_id": str(user_id)}

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["profile_suggested"],
            variables=variables,
            friendly_name="PolarisProfileSuggestedUsersWithPreloadableQuery",
        )

        users_data = (
            data.get("data", {})
            .get("xdt_api__v1__discover__chaining", {})
            .get("users", [])
        )

        users = []
        for u in users_data:
            if isinstance(u, dict):
                users.append({
                    "pk": u.get("pk"),
                    "username": u.get("username", ""),
                    "full_name": u.get("full_name", ""),
                    "is_verified": u.get("is_verified", False),
                    "is_private": u.get("is_private", False),
                    "follower_count": u.get("follower_count", 0),
                    "profile_pic_url": u.get("profile_pic_url", ""),
                    "social_context": u.get("social_context", ""),
                })

        return {"users": users, "count": len(users)}

    async def like_media(self, media_id: str) -> Dict[str, Any]:
        """Like a post (mutation)."""
        variables = {
            "media_id": str(media_id),
            "container_module": "single_post",
        }
        try:
            data = await self._graphql_doc_query(
                doc_id=DOC_IDS["like_media"],
                variables=variables,
                friendly_name="usePolarisLikeMediaLikeMutation",
            )
            return {"success": True, "media_id": str(media_id), "data": data}
        except Exception as e:
            logger.warning(f"Like media failed: {e}")
            return {"success": False, "media_id": str(media_id), "error": str(e)}

    async def _parse_timeline_connection(
        self,
        data: Dict,
        connection_key: str,
    ) -> Dict[str, Any]:
        """Parse timeline/reels connection edges."""
        connection = data.get("data", {}).get(connection_key, {})
        edges = connection.get("edges", [])
        page_info = connection.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            media = node.get("media", node)
            posts.append(GraphQLAPI._parse_v2_media(media))

        return {
            "posts": posts,
            "count": len(posts),
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    async def get_timeline_v2(
        self,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Home timeline via GraphQL v2."""
        if after:
            doc_id = DOC_IDS["feed_timeline_pagination"]
            friendly = "PolarisFeedRootPaginationCachedQuery_subscribe"
        else:
            doc_id = DOC_IDS["feed_timeline"]
            friendly = "PolarisFeedTimelineRootV2Query"

        variables = {
            "first": min(count, 20),
            "after": after,
            "before": None,
            "last": None,
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
            "__relay_internal__pv__PolarisFeedShareMenurelayprovider": True,
        }

        data = await self._graphql_doc_query(
            doc_id=doc_id,
            variables=variables,
            friendly_name=friendly,
        )

        return await self._parse_timeline_connection(
            data, "xdt_api__v1__feed__timeline__connection"
        )

    async def get_reels_trending_v2(
        self,
        count: int = 10,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trending reels via GraphQL v2."""
        variables = {
            "first": min(count, 12),
            "after": after,
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["feed_reels_trending"],
            variables=variables,
            friendly_name="PolarisClipsTabContentQuery_connection",
        )

        return await self._parse_timeline_connection(
            data, "xdt_api__v1__clips__trending__connection"
        )

    async def get_saved_v2(self) -> Dict[str, Any]:
        """Saved/bookmarked posts via GraphQL v2."""
        variables = {
            "first": 12,
            "last": None,
            "before": None,
            "after": None,
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        }

        data = await self._graphql_doc_query(
            doc_id=DOC_IDS["feed_saved"],
            variables=variables,
            friendly_name="PolarisSavedCollectionsContentQuery_connection",
        )

        return await self._parse_timeline_connection(
            data, "xdt_api__v1__feed__saved__connection"
        )

    # ═══════════════════════════════════════════════════════════
    # RAW QUERIES
    # ═══════════════════════════════════════════════════════════

    async def raw_query(
        self,
        query_hash: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send arbitrary GraphQL query (legacy)."""
        return await self._graphql_query(query_hash, variables)

    async def raw_doc_query(
        self,
        doc_id: str,
        variables: Dict[str, Any],
        friendly_name: str = "",
    ) -> Dict[str, Any]:
        """Send arbitrary GraphQL doc_id query (modern POST)."""
        return await self._graphql_doc_query(doc_id, variables, friendly_name)

