"""
GraphQL API
===========
Fetch data via Instagram GraphQL API.
Supports both legacy query_hash (GET) and modern doc_id (POST).

Two transport modes:
    - query_hash GET  → old style, still works for some queries
    - doc_id POST     → new style (2024+), required for newer endpoints

Full information can be retrieved with pagination via GraphQL.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Union

from ..client import HttpClient

logger = logging.getLogger("instaharvest_v2")


# ═══════════════════════════════════════════════════════════
# QUERY REGISTRIES
# ═══════════════════════════════════════════════════════════

# Legacy query_hashes (GET /graphql/query/?query_hash=...)
QUERY_HASHES = {
    "followers": "c76146de99bb02f6415203be841dd25a",
    "following": "d04b0a864b4b54837c0d870b0e77e076",
    "user_posts": "69cba40317214236af40e7efa697781d",
    "tagged_posts": "ff260833edf142571571f991cb0fcd26",
    "liked_posts": "d5d763b1e2acf209d62d22d184488e57",
    "user_reels": "303a4ac7f6bb47272571a1a111c50829",
    "saved_posts": "2ce1d673055b99c84dc0d5b62e3f30d2",
    "comments": "bc3296d1ce80a24b1b6e40b1e72903f5",
    "likers": "d5d763b1e2acf209d62d22d184488e57",
}

# Modern doc_ids (POST /graphql/query with doc_id=...)
DOC_IDS = {
    # User profile info
    "profile_info": "9496468463735694",
    # User profile posts (pagination)
    "profile_posts": "26442143102071041",
    # User reels tab
    "profile_reels": "25475393498805108",
    # User tagged posts
    "profile_tagged": "26832701866332833",
    # User hover card (mini profile popup)
    "profile_hover_card": "26120562547638331",
    # Story highlights tray
    "profile_highlights": "9814547265267853",
    # Suggested users on profile
    "profile_suggested": "25814188068245954",
    # Profile page content (full)
    "profile_page_content": "33954869174158742",
    # Mark story as seen (mutation)
    "stories_seen": "24372833149008516",
    # Like a post (mutation)
    "like_media": "23951234354462179",
    # Search initial state (trending)
    "search_null_state": "31090951390548929",
    # User feed timeline (initial load)
    "feed_timeline": "26307883352181852",
    # User feed timeline (pagination / subsequent pages)
    "feed_timeline_pagination": "26038778959150000",
    # Liked posts feed (UNVERIFIED — REST fallback available)
    "feed_liked": "9863315953735856",
    # Saved/bookmarked posts feed
    "feed_saved": "26523442937261068",
    # Hashtag feed (UNVERIFIED — REST fallback available)
    "feed_tag": "9506655819362310",
    # Reels trending feed
    "feed_reels_trending": "26136666099278270",
    # Post comments
    "media_comments": "26653752520898584",
    # Comment thread / replies (UNVERIFIED)
    "comment_thread": "37264637455117356",
    # Post likers (UNVERIFIED — REST /api/v1/media/{id}/likers/ available)
    "media_likers": "9321654614509578",
    # Followers list (UNVERIFIED — REST /api/v1/friendships/{id}/followers/ available)
    "followers": "37479062552899498",
    # Following list (UNVERIFIED — REST /api/v1/friendships/{id}/following/ available)
    "following": "37266564218498392",
    # Story reels tray
    "story_tray": "26695923807960093",
    # Post detail
    "media_detail": "8845758582119845",
    # Search suggestions
    "search_top": "36645594540471822",
    # Explore page
    "explore_grid": "32040227643110105",
}


class GraphQLAPI:
    """
    Instagram GraphQL query API.

    Supports both legacy query_hash (GET) and modern doc_id (POST).
    """

    def __init__(self, client: HttpClient):
        self._client = client

    # ═══════════════════════════════════════════════════════════
    # TRANSPORT: query_hash GET (legacy)
    # ═══════════════════════════════════════════════════════════

    def _graphql_query(
        self,
        query_hash: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send GraphQL query (GET /graphql/query/).
        Legacy transport — still works for some endpoints.

        Args:
            query_hash: GraphQL query hash
            variables: Query parameters

        Returns:
            GraphQL response (inside data key)
        """
        data = self._client.get(
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

    def _graphql_doc_query(
        self,
        doc_id: str,
        variables: Dict[str, Any],
        friendly_name: str = "",
    ) -> Dict[str, Any]:
        """
        Send GraphQL query via doc_id (POST /graphql/query).
        Modern transport — required for newer endpoints.

        Args:
            doc_id: Document ID (from DOC_IDS registry or custom)
            variables: Query variables
            friendly_name: API request name (for logging)

        Returns:
            GraphQL response
        """
        payload = {
            "variables": json.dumps(variables),
            "doc_id": doc_id,
            "fb_api_caller_class": "RelayModern",
            "server_timestamps": "true",
        }
        if friendly_name:
            payload["fb_api_req_friendly_name"] = friendly_name

        data = self._client.post(
            "/graphql/query",
            data=payload,
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query",
        )
        return data

    # ═══════════════════════════════════════════════════════════
    # FOLLOWERS / FOLLOWING
    # ═══════════════════════════════════════════════════════════

    def get_followers(
        self,
        user_id: str | int,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get followers via GraphQL (with pagination).

        Args:
            user_id: User ID
            count: How many to get (max ~50)
            after: Pagination cursor (end_cursor)

        Returns:
            dict:
                - count: Total followers count
                - users: Followers list [{username, id, is_verified, ...}]
                - has_next: Whether next page exists
                - end_cursor: Cursor for next page
        """
        variables = {
            "id": str(user_id),
            "include_reel": True,
            "fetch_mutual": True,
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = self._graphql_query(QUERY_HASHES["followers"], variables)

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

    def get_all_followers(
        self,
        user_id: str | int,
        max_count: int = 5000,
    ) -> List[Dict]:
        """
        Get ALL followers (auto-pagination).

        Args:
            user_id: User ID
            max_count: Maximum count to get

        Returns:
            list: All followers [{username, pk, is_verified, ...}]
        """
        all_users = []
        cursor = None
        while len(all_users) < max_count:
            result = self.get_followers(user_id, count=50, after=cursor)
            all_users.extend(result["users"])
            if not result["has_next"] or not result["end_cursor"]:
                break
            cursor = result["end_cursor"]
        return all_users[:max_count]

    def get_following(
        self,
        user_id: str | int,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get following via GraphQL (with pagination).

        Args:
            user_id: User ID
            count: How many to get
            after: Pagination cursor

        Returns:
            dict: {count, users, has_next, end_cursor}
        """
        variables = {
            "id": str(user_id),
            "include_reel": True,
            "fetch_mutual": True,
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = self._graphql_query(QUERY_HASHES["following"], variables)

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

    def get_all_following(
        self,
        user_id: str | int,
        max_count: int = 5000,
    ) -> List[Dict]:
        """
        Get ALL followings (auto-pagination).

        Args:
            user_id: User ID
            max_count: Maximum count to get

        Returns:
            list: All followings
        """
        all_users = []
        cursor = None
        while len(all_users) < max_count:
            result = self.get_following(user_id, count=50, after=cursor)
            all_users.extend(result["users"])
            if not result["has_next"] or not result["end_cursor"]:
                break
            cursor = result["end_cursor"]
        return all_users[:max_count]

    # ═══════════════════════════════════════════════════════════
    # POSTS (legacy query_hash)
    # ═══════════════════════════════════════════════════════════

    def get_user_posts(
        self,
        user_id: str | int,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get posts via GraphQL (legacy query_hash).

        Args:
            user_id: User ID
            count: How many to get (max ~50)
            after: Pagination cursor

        Returns:
            dict:
                - count: Total posts count
                - posts: [{shortcode, media_type, likes, comments, caption, ...}]
                - has_next: Whether next page exists
                - end_cursor: Cursor
        """
        variables = {
            "id": str(user_id),
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = self._graphql_query(QUERY_HASHES["user_posts"], variables)

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
                "media_type": node.get("__typename"),  # GraphImage, GraphVideo, GraphSidecar
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

    def get_user_posts_v2(
        self,
        username: str,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        User posts via modern doc_id (POST /graphql/query).
        Returns richer data than legacy query_hash.

        Args:
            username: Instagram username (not user_id!)
            count: How many posts to get (max 50)
            after: Pagination cursor

        Returns:
            dict:
                - posts: [{pk, code, media_type, like_count, comment_count,
                           caption, taken_at, user, image_versions, video_versions,
                           carousel_media, location, tagged_users, ...}]
                - has_next: Whether next page exists
                - end_cursor: Cursor
                - count: Number of posts on this page
        """
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

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["profile_posts"],
            variables=variables,
            friendly_name="PolarisProfilePostsTabContentQuery_connection",
        )

        # Parse the v2 response
        connection = (
            data.get("data", {})
            .get("xdt_api__v1__feed__user_timeline_graphql_connection", {})
        )

        edges = connection.get("edges", [])
        page_info = connection.get("page_info", {})

        posts = []
        for edge in edges:
            node = edge.get("node", {})
            posts.append(self._parse_v2_media(node))

        return {
            "posts": posts,
            "count": len(posts),
            "has_next": page_info.get("has_next_page", False),
            "end_cursor": page_info.get("end_cursor"),
        }

    def get_all_user_posts_v2(
        self,
        username: str,
        max_count: int = 100,
    ) -> List[Dict]:
        """
        Get ALL posts via doc_id (auto-pagination).

        Args:
            username: Instagram username
            max_count: Maximum number of posts to get

        Returns:
            list: All posts with full metadata
        """
        all_posts = []
        cursor = None
        page = 0

        while len(all_posts) < max_count:
            page += 1
            batch = min(12, max_count - len(all_posts))

            result = self.get_user_posts_v2(
                username, count=batch, after=cursor,
            )

            all_posts.extend(result["posts"])
            logger.debug(f"[GraphQL] Page {page}: got {len(result['posts'])} posts (total: {len(all_posts)})")

            if not result["has_next"] or not result["end_cursor"]:
                break

            cursor = result["end_cursor"]
            time.sleep(0.5)  # Anti-rate-limit delay

        return all_posts[:max_count]

    # ═══════════════════════════════════════════════════════════
    # MEDIA DETAIL (via doc_id)
    # ═══════════════════════════════════════════════════════════

    def get_media_detail(
        self,
        shortcode: str,
    ) -> Dict[str, Any]:
        """
        Full media detail via doc_id POST.

        Args:
            shortcode: Post shortcode (from URL)

        Returns:
            dict: Full media info with all available fields
        """
        variables = {
            "shortcode": shortcode,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["media_detail"],
            variables=variables,
            friendly_name="PolarisPostActionLoadPostQueryQuery",
        )

        item = (
            data.get("data", {})
            .get("xdt_shortcode_media", {})
        )

        if item:
            return self._parse_v2_media(item)

        return data

    # ═══════════════════════════════════════════════════════════
    # COMMENTS (via doc_id)
    # ═══════════════════════════════════════════════════════════

    def get_comments_v2(
        self,
        media_id: str | int,
        count: int = 20,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post comments via doc_id POST.
        Returns threaded comments with replies.

        Args:
            media_id: Media PK
            count: Comments per page
            after: Pagination cursor

        Returns:
            dict:
                - comments: [{text, user, created_at, like_count, replies, ...}]
                - has_next: bool
                - end_cursor: str
                - count: int
        """
        variables = {
            "media_id": str(media_id),
            "first": min(count, 50),
            "last": None,
            "after": after,
            "before": None,
            "sort_order": "popular",
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        }

        data = self._graphql_doc_query(
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

    # ═══════════════════════════════════════════════════════════
    # LIKERS (via doc_id)
    # ═══════════════════════════════════════════════════════════

    def get_likers_v2(
        self,
        shortcode: str,
        count: int = 50,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post likers via doc_id POST.

        Args:
            shortcode: Post shortcode
            count: Likers per page
            after: Pagination cursor

        Returns:
            dict: {users, count, has_next, end_cursor}
        """
        variables = {
            "shortcode": shortcode,
            "first": min(count, 50),
            "after": after,
        }

        data = self._graphql_doc_query(
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
    # TAGGED POSTS (legacy query_hash)
    # ═══════════════════════════════════════════════════════════

    def get_tagged_posts(
        self,
        user_id: str | int,
        count: int = 12,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        User tagged posts (tagged/photos of you).

        Args:
            user_id: User ID
            count: How many to get
            after: Pagination cursor

        Returns:
            dict: {count, posts, has_next, end_cursor}
        """
        variables = {
            "id": str(user_id),
            "first": min(count, 50),
        }
        if after:
            variables["after"] = after

        data = self._graphql_query(QUERY_HASHES["tagged_posts"], variables)

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
    # RAW QUERIES (any doc_id or query_hash)
    # ═══════════════════════════════════════════════════════════

    def raw_query(
        self,
        query_hash: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send arbitrary GraphQL query (legacy query_hash).

        Args:
            query_hash: GraphQL query hash string
            variables: Query variables dict

        Returns:
            Raw GraphQL response
        """
        return self._graphql_query(query_hash, variables)

    def raw_doc_query(
        self,
        doc_id: str,
        variables: Dict[str, Any],
        friendly_name: str = "",
    ) -> Dict[str, Any]:
        """
        Send arbitrary GraphQL doc_id query (modern POST).

        Args:
            doc_id: Document ID
            variables: Query variables
            friendly_name: API friendly name

        Returns:
            Raw GraphQL response
        """
        return self._graphql_doc_query(doc_id, variables, friendly_name)

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
    # HELPER: Parse timeline connection (edges/page_info)
    # ═══════════════════════════════════════════════════════════

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

    # ═══════════════════════════════════════════════════════════
    # HOVER CARD — Mini profile info (fast, lightweight)
    # ═══════════════════════════════════════════════════════════

    def get_hover_card(
        self,
        user_id: str | int,
        username: str,
    ) -> Dict[str, Any]:
        """
        Get mini profile card (hover card) — lightweight profile info.
        Fastest way to get basic profile data without full API call.

        Uses doc_id: PolarisUserHoverCardContentV2Query

        Args:
            user_id: User PK (numeric)
            username: Username string

        Returns:
            dict:
                - pk: str — user PK
                - username: str
                - full_name: str
                - biography: str
                - is_verified: bool
                - is_private: bool
                - follower_count: int
                - following_count: int
                - media_count: int
                - profile_pic_url: str
                - mutual_followers: list — common followers
                - is_following: bool — you follow them
                - is_followed_by: bool — they follow you
                - raw: dict — full unprocessed response
        """
        variables = {
            "userID": str(user_id),
            "username": username,
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["profile_hover_card"],
            variables=variables,
            friendly_name="PolarisUserHoverCardContentV2Query",
        )

        # Parse response — key is typically xdt_api__v1__users__user_id__info
        user_data = {}
        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find the user info key dynamically
        for key, val in raw_data.items():
            if isinstance(val, dict) and ("username" in val or "full_name" in val):
                user_data = val
                break

        if not user_data:
            # Fallback: try nested structures
            for key, val in raw_data.items():
                if isinstance(val, dict) and "user" in val:
                    user_data = val.get("user", {})
                    break

        friendship = user_data.get("friendship_status", {}) or {}
        mutual = user_data.get("mutual_followers", {}) or {}
        mutual_users = mutual.get("users", []) or []

        return {
            "pk": user_data.get("pk") or user_data.get("id"),
            "username": user_data.get("username", username),
            "full_name": user_data.get("full_name", ""),
            "biography": user_data.get("biography", ""),
            "is_verified": user_data.get("is_verified", False),
            "is_private": user_data.get("is_private", False),
            "follower_count": user_data.get("follower_count", 0),
            "following_count": user_data.get("following_count", 0),
            "media_count": user_data.get("media_count", 0),
            "profile_pic_url": user_data.get("profile_pic_url", ""),
            "mutual_followers": [
                {
                    "pk": u.get("pk"),
                    "username": u.get("username", ""),
                    "full_name": u.get("full_name", ""),
                    "profile_pic_url": u.get("profile_pic_url", ""),
                }
                for u in mutual_users
            ],
            "mutual_count": mutual.get("count", 0),
            "is_following": friendship.get("following", False),
            "is_followed_by": friendship.get("followed_by", False),
            "is_blocking": friendship.get("blocking", False),
            "is_muting": friendship.get("muting", False),
            "raw": user_data,
        }

    # ═══════════════════════════════════════════════════════════
    # SUGGESTED USERS — Similar accounts discovery (chaining)
    # ═══════════════════════════════════════════════════════════

    def get_suggested_users(
        self,
        user_id: str | int,
        module: str = "profile",
    ) -> Dict[str, Any]:
        """
        Get suggested/similar users based on a target profile.
        Equivalent to Instagram's "Suggested for you" section.

        Uses doc_id: PolarisProfileSuggestedUsersWithPreloadableQuery

        Args:
            user_id: Target user PK
            module: Context module (default: "profile")

        Returns:
            dict:
                - users: list of user dicts with:
                    - pk, username, full_name, is_verified, is_private
                    - profile_pic_url, follower_count
                    - social_context: str — "Followed by X and Y"
                    - is_following: bool
                - count: int
                - raw: dict
        """
        variables = {
            "module": module,
            "target_id": str(user_id),
        }

        data = self._graphql_doc_query(
            doc_id=DOC_IDS["profile_suggested"],
            variables=variables,
            friendly_name="PolarisProfileSuggestedUsersWithPreloadableQuery",
        )

        raw_data = data.get("data", {}) if isinstance(data, dict) else {}

        # Find the suggestions key dynamically
        suggestions = []
        for key, val in raw_data.items():
            if isinstance(val, dict):
                # Look for users array
                users_list = val.get("users", [])
                if users_list:
                    suggestions = users_list
                    break
                # Look for edges pattern
                edges = val.get("edges", [])
                if edges:
                    suggestions = [e.get("node", {}) for e in edges]
                    break
            elif isinstance(val, list):
                suggestions = val
                break

        users = []
        for user in suggestions:
            if not isinstance(user, dict):
                continue

            friendship = user.get("friendship_status", {}) or {}
            social_ctx = user.get("social_context", "")

            # Handle different social_context formats
            if isinstance(social_ctx, dict):
                social_ctx = social_ctx.get("text", "")
            elif isinstance(social_ctx, list):
                social_ctx = ", ".join(str(s) for s in social_ctx)

            users.append({
                "pk": user.get("pk") or user.get("id"),
                "username": user.get("username", ""),
                "full_name": user.get("full_name", ""),
                "is_verified": user.get("is_verified", False),
                "is_private": user.get("is_private", False),
                "profile_pic_url": user.get("profile_pic_url", ""),
                "follower_count": user.get("follower_count", 0),
                "social_context": social_ctx,
                "is_following": friendship.get("following", False),
                "is_followed_by": friendship.get("followed_by", False),
                "caption": user.get("biography", ""),
            })

        return {
            "users": users,
            "count": len(users),
            "raw": raw_data,
        }

    # ═══════════════════════════════════════════════════════════
    # LIKE MEDIA — Like/unlike a post (mutation)
    # ═══════════════════════════════════════════════════════════

    def like_media(
        self,
        media_id: str | int,
        container_module: str = "single_post",
    ) -> Dict[str, Any]:
        """
        Like a post via GraphQL mutation.

        Uses doc_id: usePolarisLikeMediaLikeMutation

        Args:
            media_id: Media PK (numeric)
            container_module: Context where like happened
                - "single_post" — from post detail page
                - "feed_timeline" — from home feed
                - "profile" — from profile page

        Returns:
            dict:
                - success: bool
                - media_id: str
                - raw: dict
        """
        variables = {
            "media_id": str(media_id),
            "container_module": container_module,
        }

        try:
            data = self._graphql_doc_query(
                doc_id=DOC_IDS["like_media"],
                variables=variables,
                friendly_name="usePolarisLikeMediaLikeMutation",
            )

            raw_data = data.get("data", {}) if isinstance(data, dict) else {}

            # Check for success — mutation returns the liked media info
            success = False
            for key, val in raw_data.items():
                if isinstance(val, dict):
                    # Look for liked status
                    if val.get("status") == "ok" or "media" in val:
                        success = True
                        break
                elif val is not None:
                    success = True

            # Also check if no errors
            errors = data.get("errors", []) if isinstance(data, dict) else []
            if not errors and raw_data:
                success = True

            return {
                "success": success,
                "media_id": str(media_id),
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"[GraphQL] like_media failed: {e}")
            return {
                "success": False,
                "media_id": str(media_id),
                "error": str(e),
            }
