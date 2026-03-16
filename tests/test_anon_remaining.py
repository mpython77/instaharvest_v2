"""
test_anon_remaining.py — AnonClient remaining methods + HttpClient tests
=========================================================================
Covers: search_web, get_user_reels, get_hashtag_sections, get_location_sections,
get_similar_accounts, get_highlights_tray, _get_web_profile_parsed, post_chain,
_graphql_profile_fallback, _web_post_fallback, stats, close.
Also: HttpClient init, get/post delegation, warm-up.
"""
import pytest
from unittest.mock import patch, MagicMock
from instaharvest_v2.anon_client import AnonClient, StrategyFailed


# ═══════════════════════════════════════════════════════════
# AnonClient — Search
# ═══════════════════════════════════════════════════════════
class TestSearchWeb:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {
            "users": [{"user": {"username": "cr7", "full_name": "Cristiano",
                       "pk": 123, "is_private": False, "is_verified": True,
                       "profile_pic_url": "pic", "follower_count": 600000000}}],
            "hashtags": [{"hashtag": {"name": "football", "media_count": 1000,
                         "search_result_subtitle": "1K posts"}}],
            "places": [{"place": {"title": "Stadium", "location": {"lat": 0},
                       "subtitle": "Sports"}}],
        }
        with patch.object(client, '_request', return_value=resp):
            result = client.search_web("cr7")
            assert result is not None
            assert len(result["users"]) == 1
            assert result["users"][0]["username"] == "cr7"
            assert len(result["hashtags"]) == 1
            assert len(result["places"]) == 1

    def test_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.search_web("test")
            assert result is None

    def test_strategy_failed(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("timeout")):
            result = client.search_web("test")
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Reels
# ═══════════════════════════════════════════════════════════
class TestGetUserReels:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {
            "items": [{"media": {
                "pk": "1", "id": "1_2", "shortcode": "ABC",
                "display_url": "img.jpg", "play_count": 5000,
                "view_count": 3000, "fb_play_count": 100,
                "owner": {"username": "u"},
                "caption": {"text": "reel caption"},
                "image_versions2": {"candidates": [{"url": "img"}]},
                "clips_metadata": {"music_info": {"music_asset_info": {
                    "title": "Song", "display_artist": "Artist"}}},
            }}],
            "paging_info": {"more_available": True, "max_id": "next"},
        }
        with patch.object(client, '_request', return_value=resp):
            result = client.get_user_reels(123)
            assert result is not None
            assert len(result["items"]) == 1
            assert result["items"][0]["play_count"] == 5000
            assert result["items"][0]["is_reel"] is True
            assert result["items"][0]["audio"]["title"] == "Song"
            assert result["more_available"] is True
            assert result["max_id"] == "next"

    def test_with_pagination(self, client):
        resp = {"items": [], "paging_info": {"more_available": False}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_user_reels(123, max_id="abc", count=5)
            assert result["items"] == []
            assert result["more_available"] is False

    def test_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_user_reels(123)
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Hashtag Sections
# ═══════════════════════════════════════════════════════════
class TestGetHashtagSections:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"pk": "1", "id": "1_2", "display_url": "img",
                 "caption": {"text": "hi"}, "image_versions2": {"candidates": [{"url": "img"}]}}},
            ]}}],
            "more_available": True, "next_max_id": "cursor", "media_count": 100,
        }
        with patch.object(client, 'get_web_api', return_value=resp):
            result = client.get_hashtag_sections("#football")
            assert result["tag_name"] == "football"
            assert len(result["posts"]) == 1
            assert result["more_available"] is True

    def test_none(self, client):
        with patch.object(client, 'get_web_api', return_value=None):
            result = client.get_hashtag_sections("test")
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Location Sections
# ═══════════════════════════════════════════════════════════
class TestGetLocationSections:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"pk": "1", "display_url": "img",
                 "caption": {"text": "loc post"}, "image_versions2": {"candidates": [{"url": "img"}]}}},
            ]}}],
            "location": {"pk": 12345, "name": "NYC", "address": "5th Ave",
                        "city": "New York", "lat": 40.7, "lng": -74.0},
            "more_available": False, "media_count": 50,
        }
        with patch.object(client, 'get_web_api', return_value=resp):
            result = client.get_location_sections(12345)
            assert result["location"]["name"] == "NYC"
            assert len(result["posts"]) == 1

    def test_with_pagination(self, client):
        resp = {"sections": [], "location": {}, "more_available": False}
        with patch.object(client, 'get_web_api', return_value=resp):
            result = client.get_location_sections(123, tab="ranked", max_id="abc")
            assert result["posts"] == []

    def test_none(self, client):
        with patch.object(client, 'get_web_api', return_value=None):
            result = client.get_location_sections(123)
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Similar Accounts
# ═══════════════════════════════════════════════════════════
class TestGetSimilarAccounts:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {"users": [
            {"username": "nike", "full_name": "Nike", "pk": 1, "is_private": False,
             "is_verified": True, "profile_pic_url": "pic", "follower_count": 300000000,
             "is_business": True, "category": "Sports"},
        ]}
        with patch.object(client, 'get_web_api', return_value=resp):
            result = client.get_similar_accounts(123)
            assert len(result) == 1
            assert result[0]["username"] == "nike"

    def test_none(self, client):
        with patch.object(client, 'get_web_api', return_value=None):
            result = client.get_similar_accounts(123)
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Highlights Tray
# ═══════════════════════════════════════════════════════════
class TestGetHighlightsTray:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {"tray": [
            {"id": "highlight:1", "title": "Travel", "media_count": 10,
             "cover_media": {"cropped_image_version": {"url": "cover.jpg"}},
             "created_at": 1700000000},
            {"id": "highlight:2", "title": "Food", "media_count": 5,
             "cover_media": {"url": "cover2.jpg"}, "created_at": 1700001000},
        ]}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_highlights_tray(123)
            assert len(result) == 2
            assert result[0]["title"] == "Travel"
            assert result[0]["media_count"] == 10

    def test_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_highlights_tray(123)
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — _get_web_profile_parsed
# ═══════════════════════════════════════════════════════════
class TestGetWebProfileParsed:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_full_profile(self, client):
        raw = {
            "id": "123", "username": "test", "full_name": "Test User",
            "biography": "My bio", "profile_pic_url": "pic.jpg",
            "profile_pic_url_hd": "pic_hd.jpg", "is_private": False,
            "is_verified": True, "is_business_account": True,
            "category_name": "Artist", "external_url": "http://test.com",
            "edge_followed_by": {"count": 1000},
            "edge_follow": {"count": 500},
            "edge_owner_to_timeline_media": {"count": 50, "edges": []},
            "bio_links": [{"url": "http://link.com"}],
            "pronouns": ["she/her"],
            "highlight_reel_count": 5, "has_clips": True, "has_guides": True,
            "edge_mutual_followed_by": {"count": 3},
            "business_email": "test@example.com",
            "business_phone_number": "+1234567890",
            "business_address_json": '{"city": "LA"}',
        }
        web_resp = {"data": {"user": raw}}
        with patch.object(client, '_request', return_value=web_resp):
            result = client._get_web_profile_parsed("test")
            assert result["username"] == "test"
            assert result["followers"] == 1000
            assert result["following"] == 500
            assert result["posts_count"] == 50
            assert result["is_business"] is True
            assert result["category"] == "Artist"
            assert result["highlight_count"] == 5
            assert result["has_clips"] is True
            assert result["business_email"] == "test@example.com"

    def test_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client._get_web_profile_parsed("test")
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Post Chain + Fallbacks
# ═══════════════════════════════════════════════════════════
class TestPostChain:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_docid_success(self, client):
        media = {"id": "1", "shortcode": "ABC", "display_url": "img.jpg",
                 "owner": {"username": "u"}, "edge_media_to_caption": {"edges": []}}
        with patch.object(client, 'get_graphql_docid', return_value=media):
            result = client.get_post_chain("ABC")
            assert result is not None

    def test_all_fail(self, client):
        with patch.object(client, 'get_graphql_docid', return_value=None), \
             patch.object(client, 'get_embed_data', return_value=None), \
             patch.object(client, '_graphql_post_fallback', return_value=None), \
             patch.object(client, '_web_post_fallback', return_value=None):
            result = client.get_post_chain("ABC")
            assert result is None

    def test_graphql_profile_fallback(self, client):
        resp = {"user": {"id": "1", "username": "test", "full_name": "T",
                "biography": "", "edge_followed_by": {"count": 0},
                "edge_follow": {"count": 0},
                "edge_owner_to_timeline_media": {"count": 0},
                "is_private": False, "profile_pic_url": ""}}
        with patch.object(client, 'get_graphql_public', return_value=resp):
            result = client._graphql_profile_fallback("test")
            assert result is not None

    def test_graphql_profile_fallback_none(self, client):
        with patch.object(client, 'get_graphql_public', return_value=None):
            result = client._graphql_profile_fallback("test")
            assert result is None

    def test_web_post_fallback(self, client):
        resp = {"items": [{"pk": "1", "shortcode": "ABC"}]}
        with patch.object(client, 'get_web_api', return_value=resp):
            result = client._web_post_fallback("ABC")
            assert result is not None

    def test_web_post_fallback_none(self, client):
        with patch.object(client, 'get_web_api', return_value=None):
            result = client._web_post_fallback("ABC")
            assert result is None


# ═══════════════════════════════════════════════════════════
# AnonClient — Stats + Close
# ═══════════════════════════════════════════════════════════
class TestStatsAndClose:
    def test_request_count(self):
        c = AnonClient()
        assert c.request_count == 0
        c._request_count = 10
        assert c.request_count == 10

    def test_error_count(self):
        c = AnonClient()
        assert c.error_count == 0
        c._error_count = 3
        assert c.error_count == 3

    def test_close(self):
        c = AnonClient()
        c.close()  # Should not raise

    def test_close_with_session(self):
        c = AnonClient()
        c._session = MagicMock()
        c.close()
        assert c._session is None

    def test_media_info_mobile(self):
        c = AnonClient(unlimited=True)
        resp = {"items": [{"pk": "1", "display_url": "img", "caption": {"text": "hi"},
                "image_versions2": {"candidates": [{"url": "img"}]}}]}
        with patch.object(c, '_request', return_value=resp):
            result = c.get_media_info_mobile(1)
            assert result is not None

    def test_media_info_mobile_none(self):
        c = AnonClient(unlimited=True)
        with patch.object(c, '_request', return_value=None):
            result = c.get_media_info_mobile(1)
            assert result is None


# ═══════════════════════════════════════════════════════════
# HttpClient Basic Tests (import + init)
# ═══════════════════════════════════════════════════════════
class TestHttpClientInit:
    def test_init(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = RateLimiter()
        hc = HttpClient(sm, pm, ad, rl)
        assert hc._session_mgr is sm
        assert hc._proxy_mgr is pm
        assert hc._anti_detect is ad
        assert hc._rate_limiter is rl
        assert hc._is_refreshing is False
        assert hc._warmed_sessions == set()

    def test_get_method(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = RateLimiter()
        hc = HttpClient(sm, pm, ad, rl)
        with patch.object(hc, '_request', return_value={"status": "ok"}) as mock_req:
            result = hc.get("/test/endpoint/", params={"a": "1"})
            assert result == {"status": "ok"}
            mock_req.assert_called_once()

    def test_post_method(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = RateLimiter()
        hc = HttpClient(sm, pm, ad, rl)
        with patch.object(hc, '_request', return_value={"status": "ok"}) as mock_req:
            result = hc.post("/test/", data={"key": "val"})
            assert result == {"status": "ok"}
            mock_req.assert_called_once()

    def test_rotate_curl_session(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = RateLimiter()
        hc = HttpClient(sm, pm, ad, rl)
        old_session = hc._curl_session
        new_session = hc._rotate_curl_session()
        assert new_session is not None
        assert new_session != old_session


# ═══════════════════════════════════════════════════════════
# Sync PublicAPI / API modules (import + init coverage)
# ═══════════════════════════════════════════════════════════
class TestSyncAPIModules:
    def test_public_api_import(self):
        from instaharvest_v2.api.public import PublicAPI
        assert PublicAPI is not None

    def test_growth_api_import(self):
        from instaharvest_v2.api.growth import GrowthAPI
        assert GrowthAPI is not None

    def test_export_api_import(self):
        from instaharvest_v2.api.export import ExportAPI
        assert ExportAPI is not None

    def test_automation_api_import(self):
        from instaharvest_v2.api.automation import AutomationAPI
        assert AutomationAPI is not None

    def test_analytics_api_import(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI is not None

    def test_download_api_import(self):
        from instaharvest_v2.api.download import DownloadAPI
        assert DownloadAPI is not None

    def test_bulk_download_api_import(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        assert BulkDownloadAPI is not None

    def test_upload_api_import(self):
        from instaharvest_v2.api.upload import UploadAPI
        assert UploadAPI is not None

    def test_audience_api_import(self):
        from instaharvest_v2.api.audience import AudienceAPI
        assert AudienceAPI is not None

    def test_public_data_api_import(self):
        from instaharvest_v2.api.public_data import PublicDataAPI
        assert PublicDataAPI is not None


class TestSyncPublicAPIMethods:
    """Test sync PublicAPI init and delegation."""

    def test_init(self):
        from instaharvest_v2.api.public import PublicAPI
        mock_client = MagicMock()
        api = PublicAPI(mock_client)
        assert api._client is mock_client

    def test_get_profile(self):
        from instaharvest_v2.api.public import PublicAPI
        mock_client = MagicMock()
        mock_client.get_profile_chain.return_value = {"username": "test"}
        api = PublicAPI(mock_client)
        result = api.get_profile("@Test")
        assert result["username"] == "test"

    def test_get_post_by_shortcode(self):
        from instaharvest_v2.api.public import PublicAPI
        mock_client = MagicMock()
        mock_client.get_post_chain.return_value = {"shortcode": "ABC"}
        api = PublicAPI(mock_client)
        result = api.get_post_by_shortcode("ABC")
        assert result["shortcode"] == "ABC"

    def test_search(self):
        from instaharvest_v2.api.public import PublicAPI
        mock_client = MagicMock()
        mock_client.search_web.return_value = {"users": []}
        api = PublicAPI(mock_client)
        result = api.search("test")
        assert "users" in result

    def test_get_comments(self):
        from instaharvest_v2.api.public import PublicAPI
        mock_client = MagicMock()
        mock_client.get_post_comments_graphql.return_value = {
            "edges": [{"node": {"id": "1", "text": "hi",
                      "owner": {"username": "u"},
                      "edge_liked_by": {"count": 0},
                      "edge_threaded_comments": {"count": 0}}}]
        }
        api = PublicAPI(mock_client)
        result = api.get_comments("ABC")
        assert len(result) == 1
