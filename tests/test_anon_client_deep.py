"""
test_anon_client_deep.py — AnonClient + AsyncAnonClient Deep Mock Tests
==========================================================================
Patches _request/_request_post to test ALL high-level methods without HTTP.
Covers: HTML parsing strategies, embed, GraphQL, mobile API, web API,
chain logic, batch operations, rate limiter, human delay.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from instaharvest_v2.anon_client import AnonClient, AnonRateLimiter, StrategyFailed


# ═══════════════════════════════════════════════════════════
# AnonRateLimiter
# ═══════════════════════════════════════════════════════════
class TestAnonRateLimiter:
    def test_enabled(self):
        rl = AnonRateLimiter(enabled=True)
        assert rl._enabled is True
        assert rl.check("html_parse") is True

    def test_disabled(self):
        rl = AnonRateLimiter(enabled=False)
        assert rl._enabled is False
        assert rl.check("html_parse") is True

    def test_rate_limit_hit(self):
        rl = AnonRateLimiter(enabled=True)
        # Fill up the window
        for _ in range(200):
            rl.check("test_strategy")
        # Eventually should hit limit
        # (depends on config, but test the path)

    def test_disabled_wait(self):
        rl = AnonRateLimiter(enabled=False)
        rl.wait_if_needed("test")  # Should return immediately


# ═══════════════════════════════════════════════════════════
# AnonClient Init
# ═══════════════════════════════════════════════════════════
class TestAnonClientInit:
    def test_defaults(self):
        c = AnonClient()
        assert c._unlimited is False
        assert c._request_count == 0
        assert c._error_count == 0

    def test_unlimited(self):
        c = AnonClient(unlimited=True)
        assert c._unlimited is True

    def test_custom_strategies(self):
        from instaharvest_v2.strategy import ProfileStrategy
        c = AnonClient(profile_strategies=[ProfileStrategy.HTML_PARSE])
        assert c._profile_strategies[0] == ProfileStrategy.HTML_PARSE


# ═══════════════════════════════════════════════════════════
# HTML Parse Strategy — _request patched
# ═══════════════════════════════════════════════════════════
class TestGetProfileHTML:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_login_redirect(self, client):
        with patch.object(client, '_request', return_value='"LoginAndSignupPage"'):
            result = client.get_profile_html("testuser")
            assert result is None

    def test_login_next_redirect(self, client):
        with patch.object(client, '_request', return_value='login/?next=/testuser/'):
            result = client.get_profile_html("testuser")
            assert result is None

    def test_shared_data_parse(self, client):
        shared = {
            "entry_data": {
                "ProfilePage": [{
                    "graphql": {
                        "user": {
                            "id": "123", "username": "test",
                            "full_name": "Test", "biography": "bio",
                            "edge_followed_by": {"count": 100},
                            "edge_follow": {"count": 50},
                            "edge_owner_to_timeline_media": {"count": 10},
                            "is_private": False, "is_verified": True,
                            "profile_pic_url": "pic",
                        }
                    }
                }]
            }
        }
        html = f'window._sharedData = {json.dumps(shared)};</script>'
        with patch.object(client, '_request', return_value=html):
            result = client.get_profile_html("test")
            assert result is not None
            assert result["username"] == "test"
            assert result["_strategy"] == "html_parse"

    def test_ld_json_parse(self, client):
        ld = {"alternateName": "@testuser", "name": "Test User",
              "description": "My bio", "image": "pic.jpg", "url": "url"}
        html = f'<script type="application/ld+json"> {json.dumps(ld)} </script>'
        with patch.object(client, '_request', return_value=html):
            result = client.get_profile_html("testuser")
            assert result is not None
            assert result["username"] == "testuser"

    def test_meta_tags_fallback(self, client):
        html = '''
        <meta property="og:title" content="Test (@testuser) • Instagram photos and videos" />
        <meta property="og:description" content="100 Followers, 50 Following, 10 Posts" />
        '''
        with patch.object(client, '_request', return_value=html):
            result = client.get_profile_html("testuser")
            # meta_tags parser returns what it can

    def test_empty_html(self, client):
        with patch.object(client, '_request', return_value='<html></html>'):
            result = client.get_profile_html("testuser")
            assert result is None

    def test_none_response(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_profile_html("testuser")
            assert result is None

    def test_strategy_failed(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("auth")):
            result = client.get_profile_html("testuser")
            assert result is None


# ═══════════════════════════════════════════════════════════
# Embed Strategy
# ═══════════════════════════════════════════════════════════
class TestGetEmbedData:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_embed_with_json(self, client):
        media = {"shortcode_media": {"id": "123", "shortcode": "ABC",
                 "display_url": "img.jpg", "owner": {"username": "u"}}}
        html = f"window.__additionalDataLoaded('extra', {json.dumps(media)})"
        with patch.object(client, '_request', return_value=html):
            result = client.get_embed_data("ABC")
            assert result is not None
            assert result["_strategy"] == "embed"

    def test_embed_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_embed_data("ABC")
            assert result is None

    def test_embed_strategy_failed(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("auth")):
            result = client.get_embed_data("ABC")
            assert result is None

    def test_embed_empty_html(self, client):
        with patch.object(client, '_request', return_value='<html></html>'):
            result = client.get_embed_data("ABC")
            assert result is None


# ═══════════════════════════════════════════════════════════
# GraphQL Strategy
# ═══════════════════════════════════════════════════════════
class TestGetGraphqlPublic:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {"data": {"user": {"id": "123"}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_graphql_public("hash123", {"id": "123"})
            assert result is not None
            assert result["user"]["id"] == "123"

    def test_strategy_failed(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("auth")):
            result = client.get_graphql_public("hash", {})
            assert result is None

    def test_none_data(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_graphql_public("hash", {})
            assert result is None

    def test_user_posts_graphql(self, client):
        resp = {"data": {"user": {"edge_owner_to_timeline_media": {"count": 10, "edges": []}}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_user_posts_graphql("123")
            assert result is not None

    def test_post_comments_graphql(self, client):
        resp = {"data": {"shortcode_media": {"edge_media_to_parent_comment": {"count": 5}}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_post_comments_graphql("ABC")

    def test_hashtag_posts_graphql(self, client):
        resp = {"data": {"hashtag": {"name": "test", "edge_hashtag_to_media": {"count": 100}}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_hashtag_posts_graphql("test")


# ═══════════════════════════════════════════════════════════
# GraphQL doc_id Strategy
# ═══════════════════════════════════════════════════════════
class TestGetGraphqlDocid:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_success(self, client):
        resp = {"data": {"xdt_shortcode_media": {
            "id": "123", "shortcode": "ABC", "display_url": "img.jpg",
            "owner": {"username": "user"}, "edge_media_to_caption": {"edges": []},
        }}}
        with patch.object(client, '_request_post', return_value=resp):
            result = client.get_graphql_docid("ABC")
            assert result is not None

    def test_none_response(self, client):
        with patch.object(client, '_request_post', return_value=None):
            result = client.get_graphql_docid("ABC")
            assert result is None

    def test_strategy_failed(self, client):
        with patch.object(client, '_request_post', side_effect=StrategyFailed("timeout")):
            result = client.get_graphql_docid("ABC")
            assert result is None

    def test_no_media(self, client):
        resp = {"data": {"xdt_shortcode_media": None}}
        with patch.object(client, '_request_post', return_value=resp):
            result = client.get_graphql_docid("ABC")
            assert result is None


# ═══════════════════════════════════════════════════════════
# Mobile API Strategy
# ═══════════════════════════════════════════════════════════
class TestMobileAPI:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_get_mobile_api(self, client):
        resp = {"status": "ok", "user": {"pk": 123}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_mobile_api("/users/123/info/")
            assert result["status"] == "ok"

    def test_get_mobile_api_failure(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("auth")):
            result = client.get_mobile_api("/users/123/info/")
            assert result is None

    def test_user_info_mobile(self, client):
        resp = {"user": {"pk": 123, "username": "test", "full_name": "Test"}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_user_info_mobile(123)
            assert result["pk"] == 123

    def test_user_info_mobile_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_user_info_mobile(123)
            assert result is None

    def test_user_feed_mobile(self, client):
        resp = {"items": [{"pk": "1", "caption": {"text": "hi"}}],
                "next_max_id": "abc", "more_available": True, "num_results": 1}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_user_feed_mobile("123")
            assert result is not None
            assert "items" in result

    def test_user_feed_mobile_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_user_feed_mobile("123")
            assert result is None


# ═══════════════════════════════════════════════════════════
# Web API Strategy
# ═══════════════════════════════════════════════════════════
class TestWebAPI:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_get_web_api(self, client):
        resp = {"data": {"user": {"id": "123"}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_web_api("/users/web_profile_info/", {"username": "test"})
            assert result is not None

    def test_get_web_api_failure(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("auth")):
            result = client.get_web_api("/users/web_profile_info/")
            assert result is None

    def test_get_web_profile(self, client):
        resp = {"data": {"user": {"id": "123", "username": "test"}}}
        with patch.object(client, '_request', return_value=resp):
            result = client.get_web_profile("test")
            assert result is not None
            assert result["id"] == "123"

    def test_get_web_profile_none(self, client):
        with patch.object(client, '_request', return_value=None):
            result = client.get_web_profile("test")
            assert result is None


# ═══════════════════════════════════════════════════════════
# Profile Chain
# ═══════════════════════════════════════════════════════════
class TestProfileChain:
    @pytest.fixture
    def client(self):
        return AnonClient(unlimited=True)

    def test_web_api_success(self, client):
        web_data = {"data": {"user": {
            "id": "123", "username": "test", "full_name": "Test",
            "biography": "bio", "edge_followed_by": {"count": 100},
            "edge_follow": {"count": 50},
            "edge_owner_to_timeline_media": {"count": 10, "edges": []},
            "is_private": False, "profile_pic_url": "pic",
        }}}
        with patch.object(client, '_request', return_value=web_data):
            result = client.get_profile_chain("test")
            assert result is not None

    def test_all_fail(self, client):
        with patch.object(client, '_request', side_effect=StrategyFailed("fail")):
            result = client.get_profile_chain("test")
            assert result is None


# ═══════════════════════════════════════════════════════════
# Human Delay
# ═══════════════════════════════════════════════════════════
class TestHumanDelay:
    def test_unlimited_skips(self):
        c = AnonClient(unlimited=True)
        c._human_delay()  # Should return immediately

    def test_normal_mode(self):
        c = AnonClient(unlimited=False)
        c._human_delay()  # Patched by conftest → no actual sleep


# ═══════════════════════════════════════════════════════════
# StrategyFailed
# ═══════════════════════════════════════════════════════════
class TestStrategyFailed:
    def test_exception(self):
        e = StrategyFailed("test msg")
        assert str(e) == "test msg"
        assert isinstance(e, Exception)


# ═══════════════════════════════════════════════════════════
# Parse delegators
# ═══════════════════════════════════════════════════════════
class TestParseDelegators:
    def test_parse_count(self):
        c = AnonClient()
        assert c._parse_count("1.5K") == 1500

    def test_parse_meta_tags_empty(self):
        c = AnonClient()
        assert c._parse_meta_tags("") == {}

    def test_parse_timeline_edges(self):
        c = AnonClient()
        assert c._parse_timeline_edges([]) == []

    def test_parse_graphql_user(self):
        c = AnonClient()
        user = {"id": "1", "username": "test", "full_name": "Test",
                "biography": "", "edge_followed_by": {"count": 0},
                "edge_follow": {"count": 0},
                "edge_owner_to_timeline_media": {"count": 0},
                "is_private": False, "profile_pic_url": ""}
        result = c._parse_graphql_user(user)
        assert result["username"] == "test"
