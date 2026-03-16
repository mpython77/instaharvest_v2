"""
GraphQL Queries
===============
Read-only query methods: followers, following, posts, comments, likers,
tagged posts, media detail, hover card, suggested users, raw queries.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .registries import QUERY_HASHES, DOC_IDS
from .transport import GraphQLTransport
from .parsers import GraphQLParsers

logger = logging.getLogger("instaharvest_v2")


class GraphQLQueries(GraphQLTransport, GraphQLParsers):
    """Read-only GraphQL query methods."""

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
            friendly_name="LikersQuery",
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
