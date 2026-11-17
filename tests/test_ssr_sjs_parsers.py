"""Tests for 2025/2026 Instagram SSR `data-sjs` HTML parsers and fallbacks."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from instaharvest_v2 import parsers
from instaharvest_v2.anon_client import AnonClient
from instaharvest_v2.async_anon_client import AsyncAnonClient
from instaharvest_v2.api.public import PublicAPI
from instaharvest_v2.api.async_public import AsyncPublicAPI


def _sjs_html(payloads):
    scripts = "\n".join(
        f'<script type="application/json" data-sjs>{json.dumps(p)}</script>'
        for p in payloads
    )
    return (
        '<html><head>'
        '<title>Cristiano Ronaldo (@cristiano) • Instagram photos and videos</title>'
        '<meta property="og:description" content="681M Followers, 652 Following, 4,157 Posts" />'
        '<meta property="og:image" content="https://cdn.example/pic.jpg" />'
        '</head><body>'
        '<a href="/accounts/login/?next=%2Fcristiano%2F">Log in</a>'
        f'{scripts}</body></html>'
    )


class TestSSRProfileHTML:
    def test_parse_profile_html_ignores_footer_login_next_and_parses_sjs(self):
        sjs_profile = {
            "require": [[0, 0, 0, [{
                "__bbox": {"result": {"data": {"xig_user_by_username": {
                    "pk": "173560420",
                    "id": "17841401692602711",
                    "username": "cristiano",
                    "full_name": "Cristiano Ronaldo",
                    "biography": "SIUUU",
                    "is_private": False,
                    "is_verified": True,
                    "follower_count": 681108270,
                    "following_count": 638,
                    "all_media_count": None,
                    "profile_pic_url": "https://cdn.example/pic.jpg",
                    "bio_links": [{"title": "Site", "url": "https://cr7.example"}],
                }}}}
            }]]]
        }
        sjs_timeline = {
            "require": [[0, 0, 0, [{
                "__bbox": {"result": {"data": {"xig_user_by_username": {
                    "pk": "173560420",
                    "polaris_ordered_timeline_connection": {
                        "edges": [{
                            "node": {
                                "__typename": "XIGPolarisVideoMedia",
                                "pk": "4031829825584708958",
                                "code": "Dfz791kzT1e",
                                "media_type": 2,
                                "product_type": "clips",
                                "caption": {"text": "Hello @nike"},
                                "display_uri": "https://cdn.example/post.jpg",
                                "user": {"pk": "173560420", "username": "cristiano"},
                            }
                        }]
                    },
                }}}}
            }]]]
        }
        html = _sjs_html([sjs_profile, sjs_timeline])
        res = parsers.parse_profile_html(html, username="cristiano")
        assert res is not None
        assert res["_strategy"] == "html_parse"
        assert res["user_id"] == "173560420"
        assert res["followers"] == 681108270
        assert res["following"] == 638
        assert res["posts_count"] == 4157  # enriched from meta tags when all_media_count is None
        assert res["is_verified"] is True
        assert len(res["recent_posts"]) == 1
        assert res["recent_posts"][0]["shortcode"] == "Dfz791kzT1e"
        assert res["recent_posts"][0]["mentions"] == ["nike"]

    def test_true_login_redirect_still_returns_none(self):
        login_html = (
            '<html><head><title>Instagram</title>'
            '<meta property="og:image" content="https://static.cdninstagram.com/rsrc.php/logo.png" />'
            '</head><body><a href="/accounts/login/?next=%2Fcristiano%2F">Log in</a></body></html>'
        )
        assert parsers.parse_profile_html(login_html, username="cristiano") is None
        assert parsers.parse_profile_html('"LoginAndSignupPage"', username="x") is None
        assert parsers.parse_profile_html('login/?next=/x/', username="x") is None


class TestSSRMediaHashtagLocation:
    def test_parse_polaris_media_sjs(self):
        payload = {
            "xig_polaris_media": {
                "__typename": "XIGPolarisVideoMedia",
                "pk": "4031829825584708958",
                "code": "Dfz791kzT1e",
                "if_not_gated_logged_out": {
                    "pk": "4031829825584708958",
                    "code": "Dfz791kzT1e",
                    "media_type": 2,
                    "product_type": "clips",
                    "like_count": 6780396,
                    "comment_count": 113387,
                    "taken_at": 1794851683,
                    "caption": {"text": "Test caption @friend"},
                    "display_uri": "https://cdn.example/thumb.jpg",
                    "image_versions2": {"candidates": [{"url": "https://cdn.example/hd.jpg", "width": 1080, "height": 1920}]},
                    "video_versions": [{"url": "https://cdn.example/vid.mp4"}],
                    "user": {"pk": "173560420", "username": "cristiano"},
                },
                "comments_connection": {
                    "edges": [{
                        "node": {
                            "pk": "999",
                            "text": "Nice!",
                            "created_at": 1794941514,
                            "user": {"pk": "42", "username": "fan1", "is_verified": False},
                        }
                    }]
                },
            }
        }
        html = f'<script type="application/json" data-sjs>{json.dumps(payload)}</script>'
        post = parsers.parse_polaris_media_sjs(html, shortcode="Dfz791kzT1e")
        assert post is not None
        assert post["likes"] == 6780396
        assert post["comments_count"] == 113387
        assert post["video_url"] == "https://cdn.example/vid.mp4"
        assert post["owner"]["username"] == "cristiano"
        assert len(post["comments"]) == 1
        assert post["comments"][0]["username"] == "fan1"

    def test_parse_hashtag_sjs(self):
        payload = {
            "xig_logged_out_popular_search_media_info": {
                "edges": [{
                    "node": {
                        "pk": "111",
                        "code": "ABC123",
                        "media_type": 1,
                        "caption": {"text": "#fashion"},
                        "display_uri": "https://cdn.example/h.jpg",
                        "user": {"pk": "7", "username": "creator"},
                    }
                }],
                "page_info": {"has_next_page": True, "end_cursor": "CUR"},
            }
        }
        html = f'<script type="application/json" data-sjs>{json.dumps(payload)}</script>'
        res = parsers.parse_hashtag_sjs(html, "Fashion")
        assert res is not None
        assert res["tag_name"] == "fashion"
        assert len(res["posts"]) == 1
        assert res["posts"][0]["shortcode"] == "ABC123"
        assert res["more_available"] is True

    def test_parse_location_sjs(self):
        payload = {
            "xdt_location_get_web_info": {
                "native_location_data": {
                    "location_info": {
                        "location_id": "213385402",
                        "name": "London, United Kingdom",
                        "media_count": 100,
                        "lat": 51.5,
                        "lng": -0.1,
                    }
                }
            },
            "xdt_location_get_web_info_tab": {
                "edges": [{
                    "node": {
                        "pk": "222",
                        "code": "LOC1",
                        "media_type": 1,
                        "caption": {"text": "London"},
                        "image_versions2": {"candidates": [{"url": "https://cdn.example/l.jpg", "width": 640, "height": 640}]},
                    }
                }],
                "page_info": {"has_next_page": False, "end_cursor": None},
            },
        }
        html = f'<script type="application/json" data-sjs>{json.dumps(payload)}</script>'
        res = parsers.parse_location_sjs(html, 213385402)
        assert res is not None
        assert res["location"]["name"] == "London, United Kingdom"
        assert len(res["posts"]) == 1
        assert res["posts"][0]["shortcode"] == "LOC1"


class TestPublicFallbacks:
    def test_sync_public_fallbacks(self):
        client = AnonClient(unlimited=True)
        api = PublicAPI(client)
        with patch.object(client, "get_graphql_docid", return_value=None), \
             patch.object(client, "_request", side_effect=[
            '<div class="EmbeddedMediaImage"><img src="img.jpg"/></div>',
            f'<script type="application/json" data-sjs>{json.dumps({"xig_polaris_media": {"pk": "1", "code": "SC1", "if_not_gated_logged_out": {"pk": "1", "code": "SC1", "like_count": 10}}})}</script>',
        ]):
            post = api.get_post_by_shortcode("SC1")
            assert post["likes"] == 10

        with patch.object(client, "get_hashtag_sections", return_value=None), \
             patch.object(client, "get_hashtag_html", return_value={"tag_name": "t", "posts": [{"pk": "1"}], "more_available": False, "media_count": 1}):
            res = api.get_hashtag_posts_v2("t")
            assert len(res["posts"]) == 1

        with patch.object(client, "get_location_sections", return_value=None), \
             patch.object(client, "get_location_html", return_value={"location": {"name": "NY"}, "posts": [{"pk": "2"}], "more_available": False, "media_count": 1}):
            res = api.get_location_posts(1)
            assert res["location"]["name"] == "NY"

    def test_async_public_fallbacks(self):
        client = AsyncAnonClient(unlimited=True)
        api = AsyncPublicAPI(client)

        async def _run():
            with patch.object(client, "get_graphql_docid", new=AsyncMock(return_value=None)), \
                 patch.object(client, "_request", new=AsyncMock(side_effect=[
                None,
                f'<script type="application/json" data-sjs>{json.dumps({"xig_polaris_media": {"pk": "1", "code": "SC2", "if_not_gated_logged_out": {"pk": "1", "code": "SC2", "like_count": 5}}})}</script>',
            ])):
                post = await api.get_post_by_shortcode("SC2")
                assert post["likes"] == 5

            with patch.object(client, "get_hashtag_sections", new=AsyncMock(return_value=None)), \
                 patch.object(client, "get_hashtag_html", new=AsyncMock(return_value={"tag_name": "t", "posts": [{"pk": "1"}], "more_available": False, "media_count": 1})):
                res = await api.get_hashtag_posts_v2("t")
                assert len(res["posts"]) == 1

            with patch.object(client, "get_location_sections", new=AsyncMock(return_value=None)), \
                 patch.object(client, "get_location_html", new=AsyncMock(return_value={"location": {"name": "London"}, "posts": [{"pk": "2"}], "more_available": False, "media_count": 1})):
                res = await api.get_location_posts(1)
                assert res["location"]["name"] == "London"

        asyncio.run(_run())
