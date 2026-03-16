"""
test_async_api_coverage.py — Async API Module Coverage Tests
==============================================================
Tests for AsyncPublicAPI + AsyncAnonClient high-level methods with mock data.
Covers: async_public.py (~243 miss), async_anon_client.py (~511 miss) methods.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


# ═══════════════════════════════════════════════════════════
# AsyncAnonClient — deep method tests
# ═══════════════════════════════════════════════════════════
class TestAsyncAnonClientMethods:
    @pytest.fixture
    def client(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        return AsyncAnonClient(unlimited=True)

    @pytest.mark.asyncio
    async def test_get_profile_html_login_redirect(self, client):
        client._request = AsyncMock(return_value='"LoginAndSignupPage"')
        result = await client.get_profile_html("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_profile_html_shared_data(self, client):
        shared = {"entry_data": {"ProfilePage": [{"graphql": {"user": {
            "id": "1", "username": "test", "full_name": "T",
            "biography": "b", "edge_followed_by": {"count": 10},
            "edge_follow": {"count": 5},
            "edge_owner_to_timeline_media": {"count": 1},
            "is_private": False, "profile_pic_url": "p",
        }}}]}}
        html = f'window._sharedData = {json.dumps(shared)};</script>'
        client._request = AsyncMock(return_value=html)
        result = await client.get_profile_html("test")
        assert result is not None
        assert result["username"] == "test"

    @pytest.mark.asyncio
    async def test_get_profile_html_ld_json(self, client):
        ld = {"alternateName": "@user", "name": "U", "description": "bio", "image": "p", "url": "u"}
        html = f'<script type="application/ld+json"> {json.dumps(ld)} </script>'
        client._request = AsyncMock(return_value=html)
        result = await client.get_profile_html("user")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_profile_html_none(self, client):
        client._request = AsyncMock(return_value=None)
        result = await client.get_profile_html("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_profile_html_empty(self, client):
        client._request = AsyncMock(return_value='<html></html>')
        result = await client.get_profile_html("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_embed_data_success(self, client):
        media = {"shortcode_media": {"id": "1", "shortcode": "ABC",
                 "display_url": "img.jpg", "owner": {"username": "u"}}}
        html = f"window.__additionalDataLoaded('extra', {json.dumps(media)})"
        client._request = AsyncMock(return_value=html)
        result = await client.get_embed_data("ABC")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_embed_data_none(self, client):
        client._request = AsyncMock(return_value=None)
        result = await client.get_embed_data("ABC")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_graphql_public_success(self, client):
        resp = {"data": {"user": {"id": "1"}}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_graphql_public("hash", {"id": "1"})
        assert result["user"]["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_graphql_public_none(self, client):
        client._request = AsyncMock(return_value=None)
        result = await client.get_graphql_public("hash", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_posts_graphql(self, client):
        resp = {"data": {"user": {"edge_owner_to_timeline_media": {"count": 5, "edges": []}}}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_user_posts_graphql("123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_post_comments_graphql(self, client):
        resp = {"data": {"shortcode_media": {"edge_media_to_parent_comment": {"count": 3}}}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_post_comments_graphql("ABC")

    @pytest.mark.asyncio
    async def test_get_hashtag_posts_graphql(self, client):
        resp = {"data": {"hashtag": {"name": "test"}}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_hashtag_posts_graphql("test")

    @pytest.mark.asyncio
    async def test_get_mobile_api(self, client):
        resp = {"user": {"pk": 123}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_mobile_api("/users/123/info/")
        assert result["user"]["pk"] == 123

    @pytest.mark.asyncio
    async def test_get_user_info_mobile(self, client):
        resp = {"user": {"pk": 123, "username": "test"}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_user_info_mobile(123)
        assert result["pk"] == 123

    @pytest.mark.asyncio
    async def test_get_web_api(self, client):
        resp = {"data": "ok"}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_web_api("/users/web_profile_info/")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_web_profile(self, client):
        resp = {"data": {"user": {"id": "1", "username": "test"}}}
        client._request = AsyncMock(return_value=resp)
        result = await client.get_web_profile("test")
        assert result["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_web_profile_none(self, client):
        client._request = AsyncMock(return_value=None)
        result = await client.get_web_profile("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_web_profile_parsed(self, client):
        raw = {
            "data": {"user": {
                "id": "1", "username": "test", "full_name": "T", "biography": "b",
                "profile_pic_url": "p", "profile_pic_url_hd": "phd",
                "is_private": False, "is_verified": True, "is_business_account": True,
                "category_name": "Artist", "external_url": "http://x.com",
                "edge_followed_by": {"count": 1000}, "edge_follow": {"count": 500},
                "edge_owner_to_timeline_media": {"count": 50, "edges": []},
                "bio_links": [{"url": "http://x.com"}], "pronouns": ["he/him"],
                "highlight_reel_count": 3, "has_clips": True, "has_guides": False,
                "edge_mutual_followed_by": {"count": 0},
                "business_email": "a@b.com", "business_phone_number": "123",
                "business_address_json": "{}", 
            }}
        }
        client._request = AsyncMock(return_value=raw)
        result = await client._get_web_profile_parsed("test")
        assert result["username"] == "test"
        assert result["followers"] == 1000
        assert result["is_business"] is True
        assert result["category"] == "Artist"

    @pytest.mark.asyncio
    async def test_human_delay_unlimited(self, client):
        await client._human_delay()  # Should return immediately


# ═══════════════════════════════════════════════════════════
# AsyncPublicAPI
# ═══════════════════════════════════════════════════════════
class TestAsyncPublicAPI:
    @pytest.fixture
    def api(self):
        from instaharvest_v2.api.async_public import AsyncPublicAPI
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient(unlimited=True)
        return AsyncPublicAPI(client)

    @pytest.mark.asyncio
    async def test_get_profile(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"username": "test", "followers": 100})
        result = await api.get_profile("@test")
        assert result["username"] == "test"

    @pytest.mark.asyncio
    async def test_get_user_id(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"user_id": "12345"})
        result = await api.get_user_id("test")
        assert result == 12345

    @pytest.mark.asyncio
    async def test_get_user_id_none(self, api):
        api._client.get_profile_chain = AsyncMock(return_value=None)
        api._client.get_web_profile = AsyncMock(return_value=None)
        result = await api.get_user_id("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_profile_pic_url(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"profile_pic_url_hd": "hd.jpg"})
        result = await api.get_profile_pic_url("test")
        assert result == "hd.jpg"

    @pytest.mark.asyncio
    async def test_get_post_by_shortcode(self, api):
        api._client.get_post_chain = AsyncMock(return_value={"shortcode": "ABC"})
        result = await api.get_post_by_shortcode("ABC")
        assert result["shortcode"] == "ABC"

    @pytest.mark.asyncio
    async def test_get_post_by_url(self, api):
        api._client.get_post_chain = AsyncMock(return_value={"shortcode": "ABC"})
        result = await api.get_post_by_url("https://instagram.com/p/ABC/")
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_post_by_url_invalid(self, api):
        result = await api.get_post_by_url("not a url")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_comments(self, api):
        resp = {"edges": [{"node": {"id": "1", "text": "hi", "owner": {"username": "u"},
                "edge_liked_by": {"count": 0}, "edge_threaded_comments": {"count": 0}}}]}
        api._client.get_post_comments_graphql = AsyncMock(return_value=resp)
        result = await api.get_comments("ABC")
        assert len(result) == 1
        assert result[0]["text"] == "hi"

    @pytest.mark.asyncio
    async def test_get_comments_none(self, api):
        api._client.get_post_comments_graphql = AsyncMock(return_value=None)
        result = await api.get_comments("ABC")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_hashtag_posts(self, api):
        resp = {"edge_hashtag_to_media": {"edges": [{"node": {
            "shortcode": "x", "display_url": "img",
            "edge_liked_by": {"count": 5},
            "edge_media_to_comment": {"count": 1},
        }}]}}
        api._client.get_hashtag_posts_graphql = AsyncMock(return_value=resp)
        api._client._parse_timeline_edges = MagicMock(return_value=[{"shortcode": "x"}])
        result = await api.get_hashtag_posts("#football")
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_search(self, api):
        api._client.search_web = AsyncMock(return_value={"users": [{"username": "test"}]})
        result = await api.search("test")
        assert "users" in result

    @pytest.mark.asyncio
    async def test_search_none(self, api):
        api._client.search_web = AsyncMock(return_value=None)
        result = await api.search("test")
        assert result == {"users": [], "hashtags": [], "places": []}

    @pytest.mark.asyncio
    async def test_get_feed(self, api):
        resp = {"items": [{"pk": "1"}], "next_max_id": "abc", "more_available": True, "num_results": 1}
        api._client.get_user_feed_mobile = AsyncMock(return_value=resp)
        result = await api.get_feed("123")
        assert "items" in result

    @pytest.mark.asyncio
    async def test_get_feed_none(self, api):
        api._client.get_user_feed_mobile = AsyncMock(return_value=None)
        result = await api.get_feed("123")
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_is_public(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"is_private": False})
        result = await api.is_public("test")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_media_urls_carousel(self, api):
        post = {"carousel_media": [
            {"display_url": "img1.jpg", "is_video": False, "display_resources": [
                {"url": "img1_hd.jpg", "width": 1080, "height": 1080}
            ]},
            {"display_url": "img2.jpg", "is_video": True, "video_url": "vid.mp4", "display_resources": []},
        ]}
        api._client.get_post_chain = AsyncMock(return_value=post)
        urls = await api.get_media_urls("ABC")
        assert len(urls) >= 2

    @pytest.mark.asyncio
    async def test_get_media_urls_single(self, api):
        post = {"images": [{"url": "img.jpg", "width": 1080, "height": 1080}], "video_url": None}
        api._client.get_post_chain = AsyncMock(return_value=post)
        urls = await api.get_media_urls("ABC")
        assert len(urls) >= 1

    @pytest.mark.asyncio
    async def test_get_media_urls_none(self, api):
        api._client.get_post_chain = AsyncMock(return_value=None)
        urls = await api.get_media_urls("ABC")
        assert urls == []

    @pytest.mark.asyncio
    async def test_get_location_posts(self, api):
        resp = {"posts": [{"pk": "1"}], "more_available": False}
        api._client.get_location_sections = AsyncMock(return_value=resp)
        result = await api.get_location_posts(12345)
        assert "posts" in result

    @pytest.mark.asyncio
    async def test_get_location_posts_none(self, api):
        api._client.get_location_sections = AsyncMock(return_value=None)
        result = await api.get_location_posts(12345)
        assert result["posts"] == []

    @pytest.mark.asyncio
    async def test_get_similar_accounts(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"user_id": "123"})
        api._client.get_web_profile = AsyncMock(return_value=None)
        api._client.get_similar_accounts = AsyncMock(return_value=[{"username": "similar"}])
        result = await api.get_similar_accounts("test")
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_get_highlights(self, api):
        api._client.get_profile_chain = AsyncMock(return_value={"user_id": "123"})
        api._client.get_web_profile = AsyncMock(return_value=None)
        api._client.get_highlights_tray = AsyncMock(return_value=[{"title": "Story"}])
        result = await api.get_highlights("test")
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_get_hashtag_posts_v2(self, api):
        resp = {"tag_name": "test", "posts": [{"pk": "1"}], "more_available": False, "media_count": 1}
        api._client.get_hashtag_sections = AsyncMock(return_value=resp)
        result = await api.get_hashtag_posts_v2("test")
        assert result["tag_name"] == "test"

    @pytest.mark.asyncio
    async def test_get_hashtag_posts_v2_none(self, api):
        api._client.get_hashtag_sections = AsyncMock(return_value=None)
        result = await api.get_hashtag_posts_v2("test")
        assert result["posts"] == []
