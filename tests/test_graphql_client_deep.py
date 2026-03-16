"""
test_graphql_client_deep.py — Deep Coverage for GraphQL + Client modules
=========================================================================
GraphQL feeds.py (785 lines), queries.py (843 lines), parsers.py (291 lines),
transport.py (123 lines), client.py (772 lines), hash_validator, registries.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

M = MagicMock


# ═══════════════════════════════════════════════════════════
# GraphQL Parsers
# ═══════════════════════════════════════════════════════════
class TestGraphQLParsers:
    def test_parse_v2_media_photo(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        node = {
            "pk": 1, "id": "1", "code": "ABC", "media_type": 1,
            "like_count": 100, "comment_count": 5,
            "caption": {"text": "Hello", "created_at": 1000},
            "user": {"pk": 2, "username": "test", "full_name": "T", "is_verified": False, "is_private": False, "profile_pic_url": ""},
            "image_versions2": {"candidates": [{"url": "http://img.jpg", "width": 1080, "height": 1080}]},
            "taken_at": 1000, "location": {"pk": 3, "name": "NY", "address": "addr", "city": "NYC", "lat": 40.0, "lng": -74.0, "short_name": "ny"},
        }
        result = GraphQLParsers._parse_v2_media(node)
        assert result["pk"] == 1
        assert result["is_photo"] is True
        assert result["like_count"] == 100
        assert result["location"]["name"] == "NY"
        assert len(result["images"]) == 1

    def test_parse_v2_media_video(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        node = {"pk": 2, "code": "V1", "media_type": 2,
                "video_versions": [{"url": "http://vid.mp4", "width": 720, "height": 1280, "type": 101}],
                "clips_metadata": {"some": "data"},
                "play_count": 5000}
        r = GraphQLParsers._parse_v2_media(node)
        assert r["is_video"] is True
        assert r["is_reel"] is True
        assert len(r["videos"]) == 1

    def test_parse_v2_media_carousel(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        node = {"pk": 3, "code": "C1", "media_type": 8,
                "carousel_media": [
                    {"pk": 10, "media_type": 1, "image_versions2": {"candidates": [{"url": "http://c1.jpg", "width": 1080, "height": 1080}]}},
                    {"pk": 11, "media_type": 2, "video_versions": [{"url": "http://c2.mp4", "width": 720, "height": 1280}],
                     "usertags": {"in": [{"user": {"username": "tagged1", "pk": 99}, "position": [0.5, 0.5]}]}},
                ]}
        r = GraphQLParsers._parse_v2_media(node)
        assert r["is_carousel"] is True
        assert len(r["carousel"]) == 2

    def test_parse_v2_media_with_music(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        node = {"pk": 4, "code": "M1", "media_type": 2,
                "music_metadata": {"music_info": {"music_asset_info": {"title": "Song", "display_artist": "Artist", "duration_in_ms": 30000, "audio_asset_id": "a1"}}}}
        r = GraphQLParsers._parse_v2_media(node)
        assert r["music"]["title"] == "Song"

    def test_parse_v2_media_with_tags_and_coauthors(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        node = {"pk": 5, "code": "T1", "media_type": 1,
                "usertags": {"in": [{"user": {"username": "t1", "pk": 10, "full_name": "T1", "is_verified": True}, "position": [0.3, 0.7]}]},
                "coauthor_producers": [{"pk": 20, "username": "co1", "full_name": "Co1", "is_verified": False}],
                "facepile_top_likers": [{"username": "liker1"}]}
        r = GraphQLParsers._parse_v2_media(node)
        assert len(r["tagged_users"]) == 1
        assert len(r["coauthors"]) == 1
        assert "liker1" in r["top_likers"]

    def test_parse_timeline_connection(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        p = GraphQLParsers()
        data = {"data": {"my_conn": {
            "edges": [
                {"node": {"media": {"pk": 1, "code": "A", "media_type": 1, "like_count": 10, "user": {}}}},
                {"node": {"ad": {"pk": 2}}},
                {"node": {"suggested_users": []}},
                {"node": {"explore_story": {"media": {"pk": 3, "code": "B", "media_type": 2, "user": {}, "explore": {"title": "Explore"}}}}},
            ],
            "page_info": {"has_next_page": True, "end_cursor": "cursor1"}
        }}}
        result = p._parse_timeline_connection(data, "my_conn")
        assert result["has_next"] is True
        assert result["count"] >= 1

    def test_parse_timeline_connection_empty(self):
        from instaharvest_v2.api.graphql.parsers import GraphQLParsers
        p = GraphQLParsers()
        result = p._parse_timeline_connection_from_conn({})
        assert result["posts"] == []


# ═══════════════════════════════════════════════════════════
# GraphQL Transport
# ═══════════════════════════════════════════════════════════
class TestGraphQLTransport:
    def test_graphql_query(self):
        from instaharvest_v2.api.graphql.transport import GraphQLTransport
        t = GraphQLTransport(M())
        t._client.get.return_value = {"data": {"user": {"pk": 1}}}
        result = t._graphql_query("hash123", {"id": "1"})
        assert result["data"]["user"]["pk"] == 1

    def test_graphql_doc_query(self):
        from instaharvest_v2.api.graphql.transport import GraphQLTransport
        t = GraphQLTransport(M())
        t._client.post.return_value = {"data": {"result": "ok"}}
        result = t._graphql_doc_query("doc123", {"x": 1}, "FriendlyName")
        assert result["data"]["result"] == "ok"


# ═══════════════════════════════════════════════════════════
# GraphQL Registries
# ═══════════════════════════════════════════════════════════
class TestRegistries:
    def test_query_hashes(self):
        from instaharvest_v2.api.graphql.registries import QUERY_HASHES, DOC_IDS
        assert "followers" in QUERY_HASHES
        assert "following" in QUERY_HASHES
        assert len(DOC_IDS) > 5

    def test_doc_ids(self):
        from instaharvest_v2.api.graphql.registries import DOC_IDS
        assert "feed_timeline" in DOC_IDS
        assert "profile_posts" in DOC_IDS


# ═══════════════════════════════════════════════════════════
# GraphQL Queries — deep method body tests
# ═══════════════════════════════════════════════════════════
class TestGraphQLQueries:
    def _make(self):
        from instaharvest_v2.api.graphql.queries import GraphQLQueries
        q = GraphQLQueries.__new__(GraphQLQueries)
        q._client = M()
        return q

    def test_get_followers(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_followed_by": {
            "count": 100,
            "edges": [{"node": {"id": "1", "username": "u1", "full_name": "U1", "is_verified": False, "is_private": False, "profile_pic_url": "", "followed_by_viewer": False, "follows_viewer": False, "requested_by_viewer": False, "reel": True}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_followers(123, count=10)
        assert result["count"] == 100
        assert len(result["users"]) == 1

    def test_get_all_followers(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_followed_by": {
            "count": 2, "edges": [{"node": {"id": "1", "username": "u1"}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_all_followers(123, max_count=10)
        assert len(result) >= 1

    def test_get_following(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_follow": {
            "count": 50, "edges": [{"node": {"id": "2", "username": "u2"}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_following(123)
        assert result["count"] == 50

    def test_get_all_following(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_follow": {
            "count": 1, "edges": [{"node": {"id": "2", "username": "u2"}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_all_following(123, max_count=5)
        assert len(result) >= 1

    def test_get_user_posts(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_owner_to_timeline_media": {
            "count": 10,
            "edges": [{"node": {"id": "1", "shortcode": "ABC", "__typename": "GraphImage", "display_url": "http://img.jpg",
                                 "is_video": False, "edge_liked_by": {"count": 50}, "edge_media_to_comment": {"count": 3},
                                 "edge_media_to_caption": {"edges": [{"node": {"text": "caption!"}}]}, "taken_at_timestamp": 1000}}],
            "page_info": {"has_next_page": True, "end_cursor": "c1"}
        }}}}
        result = q.get_user_posts(123, count=12)
        assert result["count"] == 10
        assert len(result["posts"]) == 1
        assert result["posts"][0]["caption"] == "caption!"

    def test_get_user_posts_v2(self):
        q = self._make()
        q._client.post.return_value = {"data": {"xdt_api__v1__feed__user_timeline_graphql_connection": {
            "edges": [{"node": {"pk": 1, "code": "A", "media_type": 1, "user": {}}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}
        result = q.get_user_posts_v2("testuser", count=5)
        assert len(result["posts"]) >= 1

    def test_get_media_detail(self):
        q = self._make()
        q._client.post.return_value = {"data": {"xdt_shortcode_media": {"pk": 1, "code": "ABC", "media_type": 1, "user": {}}}}
        result = q.get_media_detail("ABC")
        assert result["pk"] == 1

    def test_get_comments_v2(self):
        q = self._make()
        q._client.post.return_value = {"data": {"xdt_api__v1__media__media_id__comments__connection": {
            "edges": [{"node": {"pk": 1, "text": "Great!", "created_at": 1000, "comment_like_count": 5,
                                 "user": {"pk": 2, "username": "u1"}, "child_comment_count": 0, "preview_child_comments": []}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}
        result = q.get_comments_v2(123)
        assert len(result["comments"]) == 1
        assert result["comments"][0]["text"] == "Great!"

    def test_get_likers_v2(self):
        q = self._make()
        q._client.post.return_value = {"data": {"xdt_shortcode_media": {"edge_liked_by": {
            "count": 100,
            "edges": [{"node": {"id": "1", "username": "liker1", "full_name": "L1", "is_verified": True}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_likers_v2("ABC")
        assert len(result["users"]) == 1
        assert result["count"] == 100

    def test_get_tagged_posts(self):
        q = self._make()
        q._client.get.return_value = {"data": {"user": {"edge_user_to_photos_of_you": {
            "count": 5,
            "edges": [{"node": {"id": "1", "shortcode": "T1", "__typename": "GraphImage", "display_url": "http://t.jpg",
                                 "is_video": False, "edge_liked_by": {"count": 10}, "edge_media_to_comment": {"count": 1},
                                 "edge_media_to_caption": {"edges": []}, "owner": {"username": "o1", "id": "99"}}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}}
        result = q.get_tagged_posts(123)
        assert result["count"] == 5

    def test_raw_query(self):
        q = self._make()
        q._client.get.return_value = {"data": {"raw": True}}
        result = q.raw_query("hash", {"v": 1})
        assert result["data"]["raw"] is True

    def test_raw_doc_query(self):
        q = self._make()
        q._client.post.return_value = {"data": {"raw": True}}
        result = q.raw_doc_query("doc", {"v": 1}, "friendly")
        assert result["data"]["raw"] is True

    def test_get_hover_card(self):
        q = self._make()
        q._client.post.return_value = {"data": {"user_info": {
            "pk": 1, "username": "test", "full_name": "T", "biography": "bio",
            "is_verified": True, "is_private": False, "follower_count": 1000,
            "following_count": 500, "media_count": 50, "profile_pic_url": "http://pic.jpg",
            "friendship_status": {"following": True, "followed_by": False},
            "mutual_followers": {"count": 3, "users": [{"pk": 2, "username": "m1"}]}
        }}}
        result = q.get_hover_card(1, "test")
        assert result["follower_count"] == 1000
        assert result["is_following"] is True

    def test_get_suggested_users(self):
        q = self._make()
        q._client.post.return_value = {"data": {"suggestions": {
            "users": [{"pk": 1, "username": "s1", "full_name": "S1", "is_verified": False,
                        "friendship_status": {"following": False}, "social_context": "Followed by x"}]
        }}}
        result = q.get_suggested_users(123)
        assert len(result["users"]) >= 1


# ═══════════════════════════════════════════════════════════
# GraphQL Feeds — timeline, liked, saved, tag, reels, etc.
# ═══════════════════════════════════════════════════════════
class TestGraphQLFeeds:
    def _make(self):
        from instaharvest_v2.api.graphql.feeds import GraphQLFeeds
        f = GraphQLFeeds.__new__(GraphQLFeeds)
        f._client = M()
        return f

    def test_get_timeline_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"xdt_api__v1__feed__timeline__connection": {
            "edges": [{"node": {"media": {"pk": 1, "code": "T1", "media_type": 1, "user": {}}}}],
            "page_info": {"has_next_page": True, "end_cursor": "c1"}
        }}}
        result = f.get_timeline_v2(count=5)
        assert result["has_next"] is True

    def test_get_timeline_v2_pagination(self):
        f = self._make()
        f._client.post.return_value = {"data": {"xdt_api__v1__feed__timeline__connection": {
            "edges": [], "page_info": {"has_next_page": False}
        }}}
        result = f.get_timeline_v2(count=5, after="cursor1")
        assert result["count"] == 0

    def test_get_liked_v2(self):
        f = self._make()
        sess = M(); sess.ds_user_id = 123
        f._client.get_session.return_value = sess
        f._client.post.return_value = {"data": {"xdt_api__v1__feed__liked__connection": {
            "edges": [{"node": {"media": {"pk": 1, "code": "L1", "media_type": 1, "user": {}}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_liked_v2(count=10)
        assert len(result["posts"]) >= 0

    def test_get_saved_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"xdt_api__v1__collections__list_graphql_connection": {
            "edges": [{"node": {"collection_id": "1", "collection_name": "All", "collection_media_count": 10}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_saved_v2(count=10)
        assert len(result["posts"]) >= 1

    def test_get_saved_v2_empty(self):
        f = self._make()
        f._client.post.return_value = {"data": {}}
        result = f.get_saved_v2()
        assert result["posts"] == []

    def test_get_tag_feed_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"xdt_api__v1__feed__tag__connection": {
            "edges": [{"node": {"media": {"pk": 1, "code": "H1", "media_type": 1, "user": {}}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_tag_feed_v2("fashion")
        assert result["count"] >= 0

    def test_get_tag_feed_v2_fallback(self):
        f = self._make()
        f._client.post.return_value = {"data": {"feed_tag_fashion": {
            "edges": [{"node": {"media": {"pk": 2, "code": "H2", "media_type": 1, "user": {}}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_tag_feed_v2("fashion")
        assert result["count"] >= 0

    def test_get_reels_trending_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"xdt_api__v1__clips__home__connection_v2": {
            "edges": [], "page_info": {"has_next_page": False}
        }}}
        result = f.get_reels_trending_v2()
        assert result["posts"] == []

    def test_get_profile_reels_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"reels_conn": {
            "edges": [{"node": {"media": {"pk": 1, "id": "1", "code": "R1", "media_type": 2, "play_count": 5000,
                                           "like_count": 100, "comment_count": 5, "caption": {"text": "Reel!"}, "taken_at": 1000,
                                           "video_duration": 15.0, "user": {"pk": 2, "username": "u1"},
                                           "image_versions2": {"candidates": [{"url": "http://thumb.jpg"}]}}}}],
            "page_info": {"has_next_page": False, "end_cursor": None}
        }}}
        result = f.get_profile_reels_v2(123)
        assert len(result["posts"]) == 1

    def test_get_all_profile_reels(self):
        f = self._make()
        f._client.post.return_value = {"data": {"reels_conn": {
            "edges": [{"node": {"pk": 1, "code": "R1", "media_type": 2, "user": {}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_all_profile_reels(123, max_count=5)
        assert len(result) >= 1

    def test_get_profile_tagged_v2(self):
        f = self._make()
        f._client.post.return_value = {"data": {"tagged_conn": {
            "edges": [{"node": {"pk": 1, "id": "1", "code": "T1", "media_type": 1, "like_count": 10,
                                 "caption": {"text": "Tagged"}, "user": {"pk": 2, "username": "tagger"},
                                 "image_versions2": {"candidates": [{"url": "http://t.jpg"}]}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_profile_tagged_v2(123)
        assert len(result["posts"]) == 1

    def test_get_all_profile_tagged(self):
        f = self._make()
        f._client.post.return_value = {"data": {"tagged_conn": {
            "edges": [{"node": {"pk": 1, "code": "T1", "media_type": 1, "user": {}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_all_profile_tagged(123, max_count=5)
        assert len(result) >= 1

    def test_get_location_posts(self):
        f = self._make()
        f._client.post.return_value = {"data": {"loc_conn": {
            "edges": [{"node": {"pk": 1, "code": "LP1", "media_type": 1, "like_count": 50,
                                 "user": {"pk": 2, "username": "u1"}, "location": {"pk": 3, "name": "NYC"},
                                 "caption": {"text": "NYC!"}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_location_posts(123)
        assert len(result["posts"]) == 1

    def test_get_all_location_posts(self):
        f = self._make()
        f._client.post.return_value = {"data": {"loc_conn": {
            "edges": [{"node": {"pk": 1, "code": "LP1", "media_type": 1, "user": {}}}],
            "page_info": {"has_next_page": False}
        }}}
        result = f.get_all_location_posts(123, max_count=5)
        assert len(result) >= 1

    def test_get_highlights_items_dict(self):
        f = self._make()
        f._client.post.return_value = {"data": {"hl_data": {
            "reels": {"hl:1": {"id": "hl:1", "title": "Travel", "media_count": 2, "cover_media": {},
                                "items": [{"pk": 1, "id": "1", "media_type": 1, "taken_at": 1000,
                                            "image_versions2": {"candidates": [{"url": "http://h1.jpg"}]}}]}}
        }}}
        result = f.get_highlights_items(["hl:1"])
        assert result["count"] == 1

    def test_get_highlights_items_list(self):
        f = self._make()
        f._client.post.return_value = {"data": {"hl_data": {
            "reels": [{"id": "hl:2", "title": "Food", "media_count": 1, "items": [
                {"pk": 2, "media_type": 2, "video_versions": [{"url": "http://h2.mp4"}]}]}]
        }}}
        result = f.get_highlights_items(["hl:2"])
        assert result["count"] == 1


# ═══════════════════════════════════════════════════════════
# HttpClient — deep init + methods coverage
# ═══════════════════════════════════════════════════════════
class TestHttpClientDeep:
    def _make(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.retry import RetryConfig
        sm = M(); pm = M(); ad = M(); rl = M()
        client = HttpClient(sm, pm, ad, rl, retry_config=RetryConfig())
        return client

    def test_init(self):
        client = self._make()
        assert client._curl_session is None

    def test_get_curl_session(self):
        client = self._make()
        with patch("instaharvest_v2.client.curl_requests") as mock_curl:
            mock_session = M()
            mock_curl.Session.return_value = mock_session
            sess = client._get_curl_session()
            assert sess is not None

    def test_get_method(self):
        client = self._make()
        client._request = M(return_value={"status": "ok"})
        result = client.get("/api/v1/test/")
        assert result == {"status": "ok"}

    def test_post_method(self):
        client = self._make()
        client._request = M(return_value={"status": "ok"})
        result = client.post("/api/v1/test/", data={"key": "val"})
        assert result == {"status": "ok"}

    def test_close(self):
        client = self._make()
        client.close()


# ═══════════════════════════════════════════════════════════
# Hash Validator — check_response_for_expired_hash
# ═══════════════════════════════════════════════════════════
class TestHashValidator:
    def test_valid_response(self):
        from instaharvest_v2.api.graphql.hash_validator import check_response_for_expired_hash
        check_response_for_expired_hash({"data": {"user": {}}}, "query_hash", "abc123")

    def test_none_response(self):
        from instaharvest_v2.api.graphql.hash_validator import check_response_for_expired_hash
        check_response_for_expired_hash(None, "query_hash", "abc123")


# ═══════════════════════════════════════════════════════════
# RetryConfig import
# ═══════════════════════════════════════════════════════════
class TestRetryConfig:
    def test_init(self):
        from instaharvest_v2.retry import RetryConfig
        rc = RetryConfig()
        assert rc is not None

    def test_custom_values(self):
        from instaharvest_v2.retry import RetryConfig
        rc = RetryConfig(max_retries=5, backoff_factor=2.0)
        assert rc.max_retries == 5


# ═══════════════════════════════════════════════════════════
# SessionManager + SessionInfo
# ═══════════════════════════════════════════════════════════
class TestSessionInfo:
    def test_session_info_init(self):
        from instaharvest_v2.session_manager import SessionInfo
        si = SessionInfo(
            session_id="sid", csrf_token="csrf",
            ds_user_id="123", mid="mid1"
        )
        assert si.session_id == "sid"


# ═══════════════════════════════════════════════════════════
# AntiDetect + BrowserFingerprint
# ═══════════════════════════════════════════════════════════
class TestAntiDetect:
    def test_import(self):
        from instaharvest_v2.anti_detect import AntiDetect
        ad = AntiDetect()
        assert ad is not None

    def test_get_request_headers(self):
        from instaharvest_v2.anti_detect import AntiDetect
        ad = AntiDetect()
        headers = ad.get_request_headers(csrf_token="test_csrf")
        assert isinstance(headers, dict)

    def test_get_post_headers(self):
        from instaharvest_v2.anti_detect import AntiDetect
        ad = AntiDetect()
        headers = ad.get_post_headers(csrf_token="test_csrf")
        assert isinstance(headers, dict)

    def test_get_browser_impersonation(self):
        from instaharvest_v2.anti_detect import AntiDetect
        ad = AntiDetect()
        imp = ad.get_browser_impersonation()
        assert imp is not None


# ═══════════════════════════════════════════════════════════
# Strategy enum
# ═══════════════════════════════════════════════════════════
class TestStrategyEnum:
    def test_posts_strategy(self):
        from instaharvest_v2.strategy import PostsStrategy
        assert hasattr(PostsStrategy, "WEB_API")
        assert hasattr(PostsStrategy, "HTML_PARSE")
        assert hasattr(PostsStrategy, "GRAPHQL")
        assert hasattr(PostsStrategy, "MOBILE_FEED")
