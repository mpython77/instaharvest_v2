"""
test_async_final_65.py — Final push to 65% — async_graphql deeper + async_anon
================================================================================
Cover remaining 340 miss from async_graphql and async_anon_client body.
"""
import pytest
import asyncio
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch

M = MagicMock

def run(coro, timeout=5):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    except Exception:
        return None
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            loop.run_until_complete(asyncio.sleep(0))
        except:
            pass
        loop.close()


# ═══════════════════════════════════════════════════════════════
# 1. _parse_v2_media — 100+ line body, cover all branches
# ═══════════════════════════════════════════════════════════════
class TestParseV2Media:
    def _api(self):
        from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
        return AsyncGraphQLAPI(AsyncMock())

    def test_photo(self):
        api = self._api()
        node = {
            "pk": "123", "id": "id1", "code": "ABC", "media_type": 1,
            "like_count": 100, "comment_count": 10, "play_count": None,
            "view_count": None, "reshare_count": None,
            "caption": {"text": "hello world", "created_at": 1700000000},
            "taken_at": 1700000000,
            "user": {"pk": "u1", "username": "poster", "full_name": "P",
                     "is_verified": True, "profile_pic_url": "pic.jpg"},
            "image_versions2": {"candidates": [
                {"width": 1080, "height": 1080, "url": "https://img.jpg"},
                {"width": 640, "height": 640, "url": "https://thumb.jpg"},
            ]},
            "video_versions": None,
            "carousel_media": None,
            "usertags": {"in": [
                {"user": {"username": "tagged1", "pk": "t1", "full_name": "T1", "is_verified": False},
                 "position": [0.5, 0.5]},
            ]},
            "location": {"pk": "loc1", "name": "NYC", "city": "New York"},
            "facepile_top_likers": [{"username": "top_liker"}],
            "coauthor_producers": [{"pk": "co1", "username": "coauthor", "full_name": "Co", "is_verified": True}],
            "music_metadata": {"music_info": {"music_asset_info": {"title": "Song", "artist_name": "Artist"}}},
            "clips_metadata": None,
            "product_type": "feed",
            "original_width": 1080, "original_height": 1080,
            "has_audio": False,
            "is_paid_partnership": False,
            "commerciality_status": "not_commercial",
            "comment_threading_enabled": True,
        }
        result = run(api._parse_v2_media(node))
        assert result["pk"] == "123"
        assert result["media_type_name"] == "photo"
        assert result["is_photo"] is True
        assert result["is_video"] is False
        assert len(result["images"]) == 2
        assert len(result["tagged_users"]) == 1
        assert result["tagged_users"][0]["username"] == "tagged1"
        assert result["top_likers"] == ["top_liker"]
        assert len(result["coauthors"]) == 1
        assert result["user"]["username"] == "poster"

    def test_video(self):
        api = self._api()
        node = {
            "pk": "456", "id": "id2", "code": "DEF", "media_type": 2,
            "like_count": 200, "comment_count": 20, "play_count": 5000,
            "caption": {"text": "video post"},
            "taken_at": 1700000001,
            "user": {"pk": "u2", "username": "vid_poster"},
            "image_versions2": {"candidates": [{"url": "thumb.jpg", "width": 720, "height": 405}]},
            "video_versions": [
                {"width": 720, "height": 405, "url": "https://vid.mp4", "type": 101},
                {"width": 360, "height": 202, "url": "https://vid_low.mp4", "type": 102},
            ],
            "clips_metadata": {"audio_type": "original_audio"},
        }
        result = run(api._parse_v2_media(node))
        assert result["media_type_name"] == "video"
        assert result["is_video"] is True
        assert result["is_reel"] is True
        assert len(result["videos"]) == 2

    def test_carousel(self):
        api = self._api()
        node = {
            "pk": "789", "code": "GHI", "media_type": 8,
            "like_count": 300, "comment_count": 30,
            "caption": {"text": "album"},
            "taken_at": 1700000002,
            "user": {"pk": "u3", "username": "album_poster"},
            "image_versions2": {"candidates": []},
            "carousel_media": [
                {"pk": "c1", "media_type": 1,
                 "image_versions2": {"candidates": [{"url": "img1.jpg", "width": 1080, "height": 1080}]},
                 "video_versions": None,
                 "usertags": {"in": [{"user": {"username": "tag_in_carousel", "pk": "tc1"}, "position": [0.3, 0.3]}]}},
                {"pk": "c2", "media_type": 2,
                 "image_versions2": {"candidates": [{"url": "thumb2.jpg", "width": 720, "height": 405}]},
                 "video_versions": [{"url": "vid2.mp4", "width": 720, "height": 405}],
                 "usertags": None},
            ],
        }
        result = run(api._parse_v2_media(node))
        assert result["media_type_name"] == "carousel"
        assert result["is_carousel"] is True
        assert len(result["carousel"]) == 2
        assert result["carousel"][0]["tagged_users"][0]["username"] == "tag_in_carousel"

    def test_minimal(self):
        api = self._api()
        node = {"pk": "999", "media_type": 1}
        result = run(api._parse_v2_media(node))
        assert result["pk"] == "999"
        assert result["caption"] == ""
        assert result["images"] == []
        assert result["videos"] == []

    def test_none_values(self):
        api = self._api()
        node = {
            "pk": "888", "media_type": 1,
            "user": None, "caption": None, "location": None,
            "music_metadata": None, "clips_metadata": None,
            "image_versions2": None, "video_versions": None,
            "carousel_media": None, "usertags": None,
            "facepile_top_likers": None, "coauthor_producers": None,
        }
        result = run(api._parse_v2_media(node))
        assert result["pk"] == "888"
        assert result["images"] == []


# ═══════════════════════════════════════════════════════════════
# 2. _parse_timeline_connection deeper — all edge types
# ═══════════════════════════════════════════════════════════════
class TestParseTimelineConnection:
    def _api(self):
        from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
        return AsyncGraphQLAPI(AsyncMock())

    def test_media_edge(self):
        api = self._api()
        conn = {
            "edges": [{"node": {"media": {
                "pk": "1", "media_type": 1, "user": {"pk": "u1", "username": "x"},
                "image_versions2": {"candidates": []},
            }}}],
            "page_info": {"has_next_page": True, "end_cursor": "c2"}
        }
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["count"] == 1
        assert result["raw_edge_types"]["media"] == 1

    def test_explore_edge(self):
        api = self._api()
        conn = {
            "edges": [{"node": {"explore_story": {"media": {
                "pk": "2", "media_type": 1, "user": {"pk": "u2", "username": "y"},
                "image_versions2": {"candidates": []},
                "explore": {"title": "Trending"},
            }}}}],
            "page_info": {"has_next_page": False}
        }
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["raw_edge_types"]["explore"] == 1

    def test_ad_edge(self):
        api = self._api()
        conn = {"edges": [{"node": {"ad": {"pk": "ad1"}}}],
                "page_info": {"has_next_page": False}}
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["raw_edge_types"]["ad"] == 1
        assert result["count"] == 0

    def test_suggested_edge(self):
        api = self._api()
        conn = {"edges": [{"node": {"suggested_users": [{"username": "s1"}]}}],
                "page_info": {"has_next_page": False}}
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["raw_edge_types"]["suggested"] == 1
        assert result["count"] == 0

    def test_other_edge(self):
        api = self._api()
        conn = {"edges": [{"node": {"unknown_type": True}}],
                "page_info": {"has_next_page": False}}
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["raw_edge_types"]["other"] == 1

    def test_empty_conn(self):
        api = self._api()
        result = run(api._parse_timeline_connection_from_conn({}))
        assert result["count"] == 0
        assert result["posts"] == []

    def test_parse_timeline_connection_wrapper(self):
        api = self._api()
        data = {"data": {"my_conn": {
            "edges": [{"node": {"media": {
                "pk": "1", "media_type": 1, "user": {"username": "x"}, "image_versions2": {"candidates": []}
            }}}],
            "page_info": {"has_next_page": False}
        }}}
        result = run(api._parse_timeline_connection(data, "my_conn"))
        assert result["count"] == 1

    def test_mixed_edges(self):
        api = self._api()
        conn = {
            "edges": [
                {"node": {"media": {"pk": "1", "media_type": 1, "user": {"username": "a"}, "image_versions2": {"candidates": []}}}},
                {"node": {"ad": {"pk": "ad1"}}},
                {"node": {"suggested_users": [{"username": "s1"}]}},
                {"node": {"explore_story": {"media": {"pk": "2", "media_type": 2, "user": {"username": "b"}, "image_versions2": {"candidates": []}}}}},
                {"node": {"unknown_key": True}},
            ],
            "page_info": {"has_next_page": True, "end_cursor": "abc"}
        }
        result = run(api._parse_timeline_connection_from_conn(conn))
        assert result["count"] == 2  # media + explore
        assert result["raw_edge_types"]["media"] == 1
        assert result["raw_edge_types"]["explore"] == 1
        assert result["raw_edge_types"]["ad"] == 1
        assert result["raw_edge_types"]["suggested"] == 1
        assert result["raw_edge_types"]["other"] == 1


# ═══════════════════════════════════════════════════════════════
# 3. get_tag_feed_v2 — fallback connection key logic
# ═══════════════════════════════════════════════════════════════
class TestTagFeed:
    def _api(self):
        from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
        return AsyncGraphQLAPI(AsyncMock())

    def test_tag_feed_v2_found(self):
        api = self._api()
        api._client.post.return_value = {"data": {"xdt_api__v1__feed__tag__connection": {
            "edges": [{"node": {"media": {"pk": "t1", "media_type": 1, "user": {"username": "x"},
                "image_versions2": {"candidates": []}}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = run(api.get_tag_feed_v2("python"))
        assert result is not None

    def test_tag_feed_v2_fallback_key(self):
        api = self._api()
        api._client.post.return_value = {"data": {
            "xdt_api__v1__feed__tag__python__connection": {
                "edges": [], "page_info": {"has_next_page": False}
            }
        }}
        result = run(api.get_tag_feed_v2("python"))
        assert result is not None

    def test_tag_feed_v2_dynamic_key(self):
        api = self._api()
        api._client.post.return_value = {"data": {
            "some_tag_related_key": {
                "edges": [], "page_info": {"has_next_page": False}
            }
        }}
        result = run(api.get_tag_feed_v2("python"))
        assert result is not None

    def test_tag_feed_v2_empty(self):
        api = self._api()
        api._client.post.return_value = {"data": {}}
        result = run(api.get_tag_feed_v2("python"))
        assert result["count"] == 0


# ═══════════════════════════════════════════════════════════════
# 4. get_reels_trending_v2
# ═══════════════════════════════════════════════════════════════
class TestReelsTrending:
    def _api(self):
        from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
        return AsyncGraphQLAPI(AsyncMock())

    def test_reels_trending(self):
        api = self._api()
        api._client.post.return_value = {"data": {"xdt_api__v1__clips__home__connection_v2": {
            "edges": [{"node": {"media": {"pk": "r1", "media_type": 2, "user": {"username": "r"},
                "image_versions2": {"candidates": []}, "clips_metadata": {"audio_type": "original"}}}}],
            "page_info": {"has_next_page": True, "end_cursor": "rc2"}
        }}}
        result = run(api.get_reels_trending_v2(count=20))
        assert result is not None

    def test_reels_trending_pagination(self):
        api = self._api()
        api._client.post.return_value = {"data": {"xdt_api__v1__clips__home__connection_v2": {
            "edges": [], "page_info": {"has_next_page": False}
        }}}
        result = run(api.get_reels_trending_v2(count=20, after="cursor"))
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# 5. ASYNC_ANON_CLIENT deeper — stats, helpers, strategy config
# ═══════════════════════════════════════════════════════════════
class TestAsyncAnonClientDeeper:
    def test_init_with_proxy(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        pm = M()
        c = AsyncAnonClient(proxy_manager=pm)
        assert c._proxy_mgr is pm

    def test_init_custom_strategies(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        c = AsyncAnonClient(profile_strategies=["web_api", "graphql"])
        assert len(c._profile_strategies) >= 1

    def test_init_posts_strategies(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        c = AsyncAnonClient(posts_strategies=["web_api"])
        assert len(c._posts_strategies) >= 1

    def test_stats_initial(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        c = AsyncAnonClient()
        assert c._request_count == 0
        assert c._error_count == 0
        assert c._traffic_bytes == 0

    def test_rate_limiter_disabled(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient, AsyncAnonRateLimiter
        c = AsyncAnonClient(unlimited=True)
        assert not c._rate_limiter._enabled

    def test_rate_limiter_enabled(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        c = AsyncAnonClient(unlimited=False)
        assert c._rate_limiter._enabled

    def test_delays_unlimited(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        from instaharvest_v2.config import ANON_REQUEST_DELAYS_UNLIMITED
        c = AsyncAnonClient(unlimited=True)
        assert c._delays is ANON_REQUEST_DELAYS_UNLIMITED

    def test_delays_normal(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        from instaharvest_v2.config import ANON_REQUEST_DELAYS
        c = AsyncAnonClient(unlimited=False)
        assert c._delays is ANON_REQUEST_DELAYS


# ═══════════════════════════════════════════════════════════════
# 6. GRAPHQL helpers deeper (QUERY_HASHES, DOC_IDS registries)
# ═══════════════════════════════════════════════════════════════
class TestGraphQLRegistries:
    def test_query_hashes(self):
        from instaharvest_v2.api.async_graphql import QUERY_HASHES
        assert "followers" in QUERY_HASHES
        assert "following" in QUERY_HASHES
        assert "user_posts" in QUERY_HASHES
        assert "comments" in QUERY_HASHES

    def test_doc_ids(self):
        from instaharvest_v2.api.async_graphql import DOC_IDS
        assert "profile_info" in DOC_IDS
        assert "profile_posts" in DOC_IDS
        assert "media_comments" in DOC_IDS
        assert "media_detail" in DOC_IDS
        assert "feed_timeline" in DOC_IDS
        assert "feed_saved" in DOC_IDS
        assert "story_tray" in DOC_IDS
        assert "explore_grid" in DOC_IDS
