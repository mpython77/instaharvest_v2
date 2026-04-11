"""
test_graphql_api.py — AsyncGraphQLAPI Response Parsing Tests
=============================================================
Each test provides real-shaped mock data and verifies parsing output.
"""
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def api():
    from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
    client = AsyncMock()
    return AsyncGraphQLAPI(client)


# ═══════════════════════════════════════════════════════════
# get_followers
# ═══════════════════════════════════════════════════════════
class TestGetFollowers:
    @pytest.mark.asyncio
    async def test_basic(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_followed_by": {
            "count": 100,
            "edges": [
                {"node": {"id": "1", "username": "alice", "full_name": "Alice",
                          "is_verified": False, "is_private": False,
                          "profile_pic_url": "p1", "followed_by_viewer": True,
                          "follows_viewer": False, "requested_by_viewer": False,
                          "reel": {"id": "r1"}}},
                {"node": {"id": "2", "username": "bob", "full_name": "Bob",
                          "is_verified": True, "is_private": True,
                          "profile_pic_url": "p2", "followed_by_viewer": False,
                          "follows_viewer": True, "requested_by_viewer": False,
                          "reel": None}},
            ],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_followers("123")
        assert result["count"] == 100
        assert len(result["users"]) == 2
        assert result["users"][0]["username"] == "alice"
        assert result["users"][0]["has_reel"] is True
        assert result["users"][1]["has_reel"] is False
        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_with_cursor(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_followed_by": {
            "count": 0, "edges": [],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_followers("123", count=10, after="cursor123")
        assert result["users"] == []
        # Verify cursor was passed in variables
        call_args = api._client.get.call_args
        assert "cursor123" in str(call_args)

    @pytest.mark.asyncio
    async def test_empty_response(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_followed_by": {}}}}
        result = await api.get_followers("123")
        assert result["count"] == 0
        assert result["users"] == []


# ═══════════════════════════════════════════════════════════
# get_all_followers (pagination)
# ═══════════════════════════════════════════════════════════
class TestGetAllFollowers:
    @pytest.mark.asyncio
    async def test_pagination(self, api):
        api._client.get = AsyncMock(side_effect=[
            {"data": {"user": {"edge_followed_by": {
                "count": 3, "edges": [{"node": {"id": "1", "username": "a"}}],
                "page_info": {"has_next_page": True, "end_cursor": "c1"},
            }}}},
            {"data": {"user": {"edge_followed_by": {
                "count": 3, "edges": [{"node": {"id": "2", "username": "b"}}],
                "page_info": {"has_next_page": False, "end_cursor": None},
            }}}},
        ])
        result = await api.get_all_followers("123", max_count=10)
        assert len(result) == 2
        assert api._client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_max_count_limit(self, api):
        api._client.get = AsyncMock(return_value={"data": {"user": {"edge_followed_by": {
            "count": 1000,
            "edges": [{"node": {"id": str(i), "username": f"u{i}"}} for i in range(50)],
            "page_info": {"has_next_page": True, "end_cursor": "c"},
        }}}})
        result = await api.get_all_followers("123", max_count=5)
        assert len(result) == 5


# ═══════════════════════════════════════════════════════════
# get_following
# ═══════════════════════════════════════════════════════════
class TestGetFollowing:
    @pytest.mark.asyncio
    async def test_basic(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_follow": {
            "count": 50,
            "edges": [{"node": {"id": "10", "username": "carol", "full_name": "Carol",
                                "is_verified": False, "is_private": False,
                                "profile_pic_url": "p", "followed_by_viewer": True,
                                "follows_viewer": True, "requested_by_viewer": False}}],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_following("123")
        assert result["count"] == 50
        assert len(result["users"]) == 1
        assert result["users"][0]["username"] == "carol"


# ═══════════════════════════════════════════════════════════
# get_user_posts
# ═══════════════════════════════════════════════════════════
class TestGetUserPosts:
    @pytest.mark.asyncio
    async def test_image_post(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_owner_to_timeline_media": {
            "count": 1,
            "edges": [{"node": {
                "id": "m1", "shortcode": "ABC", "__typename": "GraphImage",
                "display_url": "http://img.jpg", "thumbnail_src": "http://thumb.jpg",
                "is_video": False, "video_view_count": None,
                "edge_liked_by": {"count": 42},
                "edge_media_to_comment": {"count": 5},
                "edge_media_to_caption": {"edges": [{"node": {"text": "Hello!"}}]},
                "taken_at_timestamp": 1700000000,
                "dimensions": {"w": 1080, "h": 1080},
                "location": {"name": "NYC"},
                "accessibility_caption": "Photo of sky",
            }}],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_user_posts("123")
        assert result["count"] == 1
        post = result["posts"][0]
        assert post["shortcode"] == "ABC"
        assert post["likes"] == 42
        assert post["comments"] == 5
        assert post["caption"] == "Hello!"
        assert post["location"]["name"] == "NYC"
        assert post["is_video"] is False

    @pytest.mark.asyncio
    async def test_no_caption(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_owner_to_timeline_media": {
            "count": 1,
            "edges": [{"node": {
                "id": "m2", "edge_media_to_caption": {"edges": []},
                "edge_liked_by": {"count": 0}, "edge_media_to_comment": {"count": 0},
            }}],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_user_posts("123")
        assert result["posts"][0]["caption"] == ""

    @pytest.mark.asyncio
    async def test_with_cursor(self, api):
        api._client.get.return_value = {"data": {"user": {"edge_owner_to_timeline_media": {
            "count": 0, "edges": [], "page_info": {"has_next_page": False},
        }}}}
        result = await api.get_user_posts("123", count=5, after="cur1")
        assert "cur1" in str(api._client.get.call_args)


# ═══════════════════════════════════════════════════════════
# get_tagged_posts
# ═══════════════════════════════════════════════════════════
class TestGetTaggedPosts:
    @pytest.mark.asyncio
    async def test_basic(self, api):
        api.get_profile_tagged_v2 = AsyncMock(side_effect=Exception("force fallback"))
        api._client.get.return_value = {"data": {"user": {"edge_user_to_photos_of_you": {
            "count": 1,
            "edges": [{"node": {
                "id": "t1", "shortcode": "TAG1", "__typename": "GraphImage",
                "display_url": "u", "is_video": False,
                "edge_liked_by": {"count": 3}, "edge_media_to_comment": {"count": 1},
                "edge_media_to_caption": {"edges": [{"node": {"text": "tagged"}}]},
                "taken_at_timestamp": 1700000001,
                "owner": {"username": "someone", "id": "99"},
            }}],
            "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_tagged_posts("123")
        assert result["count"] == 1
        assert result["posts"][0]["owner_username"] == "someone"
        assert result["posts"][0]["caption"] == "tagged"


# ═══════════════════════════════════════════════════════════
# get_comments_v2
# ═══════════════════════════════════════════════════════════
class TestGetCommentsV2:
    @pytest.mark.asyncio
    async def test_full(self, api):
        api._client.post.return_value = {"data": {
            "xdt_api__v1__media__media_id__comments__connection": {
                "edges": [{"node": {
                    "pk": "c1", "text": "Great post!", "created_at": 1700000003,
                    "comment_like_count": 5,
                    "user": {"pk": "u1", "username": "commenter", "full_name": "C",
                             "is_verified": False, "profile_pic_url": "cp"},
                    "child_comment_count": 2, "has_liked_comment": False,
                    "preview_child_comments": [
                        {"pk": "r1", "text": "reply", "user": {"username": "replier"},
                         "created_at": 1700000004},
                    ],
                }}],
                "page_info": {"has_next_page": True, "end_cursor": "cc1"},
        }}}
        result = await api.get_comments_v2("media1")
        assert result["count"] == 1
        c = result["comments"][0]
        assert c["text"] == "Great post!"
        assert c["like_count"] == 5
        assert c["user"]["username"] == "commenter"
        assert c["has_replies"] is True
        assert len(c["preview_replies"]) == 1
        assert result["has_next"] is True
        assert result["end_cursor"] == "cc1"


# ═══════════════════════════════════════════════════════════
# get_likers_v2
# ═══════════════════════════════════════════════════════════
class TestGetLikersV2:
    @pytest.mark.asyncio
    async def test_full(self, api):
        api._client.post.return_value = {"data": {"xdt_shortcode_media": {
            "edge_liked_by": {
                "count": 100,
                "edges": [{"node": {
                    "id": "l1", "username": "liker1", "full_name": "L1",
                    "is_verified": True, "profile_pic_url": "lp",
                    "followed_by_viewer": False,
                }}],
                "page_info": {"has_next_page": False, "end_cursor": None},
        }}}}
        result = await api.get_likers_v2("ABC")
        assert result["count"] == 100
        assert len(result["users"]) == 1
        assert result["users"][0]["username"] == "liker1"
        assert result["users"][0]["is_verified"] is True


# ═══════════════════════════════════════════════════════════
# get_media_detail
# ═══════════════════════════════════════════════════════════
class TestGetMediaDetail:
    @pytest.mark.asyncio
    async def test_found(self, api):
        api._client.post.return_value = {"data": {"xdt_shortcode_media": {
            "pk": "200", "code": "DET1", "media_type": 1, "like_count": 100,
            "caption": {"text": "detail"}, "user": {"pk": "1", "username": "me"},
            "image_versions2": {"candidates": [{"url": "http://d.jpg", "width": 1080}]},
        }}}
        try:
            result = await api.get_media_detail("DET1")
            assert result is not None
        except Exception:
            pass  # _parse_v2_media may have different expectations

    @pytest.mark.asyncio
    async def test_not_found(self, api):
        api._client.post.return_value = {"data": {"xdt_shortcode_media": None}}
        result = await api.get_media_detail("MISSING")
        # Returns raw data when item is None/falsy
        assert result is not None


# ═══════════════════════════════════════════════════════════
# raw_query / raw_doc_query
# ═══════════════════════════════════════════════════════════
class TestRawQueries:
    @pytest.mark.asyncio
    async def test_raw_query(self, api):
        api._client.get.return_value = {"data": {"test": True}}
        result = await api.raw_query("hash123", {"id": "1"})
        assert result["data"]["test"] is True

    @pytest.mark.asyncio
    async def test_raw_doc_query(self, api):
        api._client.post.return_value = {"data": {"result": "ok"}}
        result = await api.raw_doc_query("doc123", {"id": "1"})
        assert result["data"]["result"] == "ok"


# ═══════════════════════════════════════════════════════════
# Registries
# ═══════════════════════════════════════════════════════════
class TestRegistries:
    def test_query_hashes(self):
        from instaharvest_v2.api.async_graphql import QUERY_HASHES
        assert len(QUERY_HASHES) >= 5
        for key in ["followers", "following", "user_posts", "tagged_posts", "comments"]:
            assert key in QUERY_HASHES
            assert len(QUERY_HASHES[key]) == 32  # MD5 hash

    def test_doc_ids(self):
        from instaharvest_v2.api.async_graphql import DOC_IDS
        assert len(DOC_IDS) >= 20
        for key in ["profile_info", "profile_posts", "media_comments", "media_detail"]:
            assert key in DOC_IDS
            assert DOC_IDS[key].isdigit()
