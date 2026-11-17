"""Tests for live-scan bug fixes and 2026 web/SSR resilience improvements."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from instaharvest_v2._endpoint_keys import endpoint_key, resolve_endpoint_key
from instaharvest_v2.anti_detect import AntiDetect
from instaharvest_v2.api.account import AccountAPI
from instaharvest_v2.api.async_account import AsyncAccountAPI
from instaharvest_v2.api.async_feed import AsyncFeedAPI
from instaharvest_v2.api.async_location import AsyncLocationAPI
from instaharvest_v2.api.async_users import AsyncUsersAPI
from instaharvest_v2.api.feed import FeedAPI
from instaharvest_v2.api.location import LocationAPI
from instaharvest_v2.api.users import UsersAPI
from instaharvest_v2.exceptions import NotFoundError, RateLimitError
from instaharvest_v2.models.base import InstaModel
from instaharvest_v2.models.notification import NotifInbox, Notification
from instaharvest_v2.models.user import User
from instaharvest_v2.parsers import (
    apply_web_html_metadata,
    build_session_verification_report,
    parse_polaris_viewer,
    parse_web_doc_ids,
    parse_web_revision,
)
from instaharvest_v2.proxy_manager import ProxyManager
from instaharvest_v2.session_manager import SessionFingerprint, SessionInfo
from instaharvest_v2.smart_rotation import SmartRotationCoordinator


def _run(coro):
    return asyncio.run(coro)


class TestNotificationAndBaseModels:
    def test_notification_base64_pk_and_float_timestamp(self):
        ts = datetime.now().timestamp() - 120
        story = {
            "pk": "IBV5l8xOBvhXGMagFNz+kw==",
            "story_type": 101,
            "notif_name": "user_followed",
            "type": 3,
            "args": {
                "text": "alice started following you.",
                "profile_id": 123456,
                "profile_name": "alice",
                "timestamp": ts,
            },
        }
        notif = Notification.from_story(story)
        assert notif.pk == "IBV5l8xOBvhXGMagFNz+kw=="
        assert isinstance(notif.timestamp, float)
        assert notif.time_ago.endswith("m ago")

    def test_notif_inbox_handles_none_fields(self):
        inbox = NotifInbox.from_response(
            {
                "counts": {"likes": 2},
                "last_checked": None,
                "continuation_token": None,
                "partition": None,
                "new_stories": [],
                "old_stories": [
                    {
                        "pk": "abc+/==",
                        "story_type": 60,
                        "notif_name": "like",
                        "type": 1,
                        "args": {"text": "liked", "timestamp": 1700000000.0},
                    }
                ],
            }
        )
        assert inbox.continuation_token == 0
        assert inbox.last_checked == 0.0
        assert len(inbox.old_notifications) == 1
        assert inbox.old_notifications[0].pk == "abc+/=="

    def test_instamodel_coerce_pk_respects_str_vs_int(self):
        class StrPkModel(InstaModel):
            pk: str = ""

        class IntPkModel(InstaModel):
            pk: int = 0

        assert StrPkModel(pk="raw_b64==").pk == "raw_b64=="
        assert IntPkModel(pk="42").pk == 42


class TestAsyncFeedAwaitsAndSavedFallback:
    @pytest.mark.asyncio
    async def test_async_feed_awaits_graphql_coroutines(self):
        client = MagicMock()
        client.get = AsyncMock(return_value={})
        gql = MagicMock()
        gql.get_timeline_v2 = AsyncMock(return_value={"posts": [{"pk": 1}], "has_next": False})
        gql.get_liked_v2 = AsyncMock(return_value={"posts": [{"pk": 2}], "has_next": False})
        gql.get_saved_v2 = AsyncMock(return_value={"posts": [{"pk": 3}], "has_next": False})
        gql.get_tag_feed_v2 = AsyncMock(return_value={"posts": [{"pk": 4}], "has_next": False})
        gql.get_reels_trending_v2 = AsyncMock(return_value={"posts": [{"pk": 5}], "has_next": False})

        api = AsyncFeedAPI(client, graphql=gql)

        assert (await api.get_timeline())["posts"] == [{"pk": 1}]
        assert (await api.get_liked())["posts"] == [{"pk": 2}]
        assert (await api.get_saved())["posts"] == [{"pk": 3}]
        assert (await api.get_tag_feed("python"))["posts"] == [{"pk": 4}]
        assert (await api.get_reels_feed())["posts"] == [{"pk": 5}]

    def test_sync_saved_falls_back_to_rest_saved_posts(self):
        client = MagicMock()
        client.get.return_value = {
            "items": [{"media": {"pk": "999", "code": "ABC"}}],
            "more_available": True,
            "next_max_id": "cur_1",
        }
        gql = MagicMock()
        gql.get_saved_v2.return_value = {"posts": [], "has_next": False, "count": 0}
        api = FeedAPI(client, graphql=gql)
        res = api.get_saved(count=5)
        assert res["count"] == 1
        assert res["posts"][0]["pk"] == "999"
        assert res["end_cursor"] == "cur_1"

    @pytest.mark.asyncio
    async def test_async_saved_falls_back_to_rest_saved_posts(self):
        client = MagicMock()
        client.get = AsyncMock(
            return_value={
                "items": [{"media": {"pk": "888", "code": "XYZ"}}],
                "more_available": False,
                "next_max_id": None,
            }
        )
        gql = MagicMock()
        gql.get_saved_v2 = AsyncMock(return_value={"posts": [], "has_next": False, "count": 0})
        api = AsyncFeedAPI(client, graphql=gql)
        res = await api.get_saved(count=5)
        assert res["count"] == 1
        assert res["posts"][0]["pk"] == "888"


class TestLocationFeedPost:
    def test_sync_location_get_feed_uses_post_with_fallback(self):
        client = MagicMock()
        client.post.return_value = {"sections": [{"id": 1}], "status": "ok"}
        api = LocationAPI(client)
        res = api.get_feed("212988663", max_id="c1")
        assert res["status"] == "ok"
        client.post.assert_called_once_with(
            "/locations/212988663/sections/",
            data={"tab": "recent", "max_id": "c1"},
            rate_category="get_feed",
        )

        # Fallback to GET if POST raises
        client.post.side_effect = RuntimeError("post rejected")
        client.get.return_value = {"sections": []}
        res2 = api.get_feed("212988663")
        assert res2 == {"sections": []}
        client.get.assert_called_once()

    def test_async_location_get_feed_uses_post(self):
        client = MagicMock()
        client.post = AsyncMock(return_value={"sections": [{"id": 2}], "status": "ok"})
        api = AsyncLocationAPI(client)
        res = _run(api.get_feed("212988663"))
        assert res["status"] == "ok"
        client.post.assert_awaited_once()


class TestEndpointKeysAndLockedRotation:
    def test_resolve_endpoint_key_isolates_graphql_operations(self):
        url = "https://www.instagram.com/graphql/query"
        k1 = resolve_endpoint_key(url, data={"fb_api_req_friendly_name": "FeedTimeline"})
        k2 = resolve_endpoint_key(url, data={"doc_id": "9863315953735856"})
        k3 = resolve_endpoint_key(url, params={"query_hash": "abc123"})
        rest = resolve_endpoint_key("https://www.instagram.com/api/v1/users/123456/info/")
        assert k1 == "www.instagram.com/graphql/query:FeedTimeline"
        assert k2 == "www.instagram.com/graphql/query:9863315953735856"
        assert k3 == "www.instagram.com/graphql/query:abc123"
        assert rest == endpoint_key("https://www.instagram.com/api/v1/users/123456/info/")

    def test_smart_rotation_locks_identity_for_session_fingerprint(self):
        ad = AntiDetect()
        pm = ProxyManager()
        coord = SmartRotationCoordinator(ad, pm)
        fp = SessionFingerprint.from_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        )
        ctx = coord.on_request_start("GET", "/api/v1/news/inbox/", 1, 3, fingerprint=fp)
        assert ctx.identity_locked is True
        assert ctx.identity_platform == "Windows"
        action = coord.on_request_error(
            ctx, RateLimitError("Spam"), status_code=400, rotate_proxy=True, rotate_identity=True
        )
        assert "LOCKED" in action

    def test_pick_random_prefers_platform(self):
        fp = SessionFingerprint.pick_random(prefer_platform="Windows")
        assert fp.sec_ch_ua_platform == '"Windows"'


class TestWebViewerAndSSRFallbacks:
    SAMPLE_HOME_HTML = (
        '<html><script>{"consistency":{"rev":1054999161},'
        '"DTSGInitialData":[],{"token":"AQF_test_dtsg"},1],'
        '"doc_id":"26631847903179252","doc_id":"26853171684350625",'
        '"PolarisViewer",[],{"data":{"id":"59451198780","username":"testuser",'
        '"full_name":"Test Name","is_private":false,"biography":"hi"}},2]</script></html>'
    )

    SAMPLE_PROFILE_HTML = (
        '<html><script type="application/json" data-sjs>'
        '{"xig_user_by_username":{"pk":"25025320","id":"17841401",'
        '"username":"instagram","full_name":"Instagram",'
        '"follower_count":686000000,"following_count":100,"all_media_count":7000,'
        '"is_verified":true,"is_private":false}}'
        "</script></html>"
    )

    def test_web_metadata_parsers_and_session_report(self):
        sess = SessionInfo(session_id="sid", csrf_token="csrf", ds_user_id="59451198780")
        assert parse_web_revision(self.SAMPLE_HOME_HTML) == "1054999161"
        assert parse_web_doc_ids(self.SAMPLE_HOME_HTML) == [
            "26631847903179252",
            "26853171684350625",
        ]
        viewer = parse_polaris_viewer(self.SAMPLE_HOME_HTML)
        assert viewer["username"] == "testuser"

        report = build_session_verification_report(self.SAMPLE_HOME_HTML, sess)
        assert report["valid"] is True
        assert report["username"] == "testuser"
        assert report["server_revision"] == "1054999161"
        assert report["has_dtsg"] is True
        assert sess.username == "testuser"
        assert sess.x_instagram_ajax == "1054999161"

    def test_account_get_current_user_uses_polaris_viewer_fallback(self):
        client = MagicMock()
        sess = SessionInfo(session_id="sid", csrf_token="csrf", ds_user_id="59451198780")
        client.get_session.return_value = sess
        client.get_html.return_value = self.SAMPLE_HOME_HTML

        api = AccountAPI(client)
        res = api.get_current_user()
        assert res["username"] == "testuser"
        assert sess.username == "testuser"
        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_account_get_current_user_uses_polaris_viewer_fallback(self):
        client = MagicMock()
        sess = SessionInfo(session_id="sid", csrf_token="csrf", ds_user_id="59451198780")
        client.get_session.return_value = sess
        client.get_html = AsyncMock(return_value=self.SAMPLE_HOME_HTML)

        api = AsyncAccountAPI(client)
        res = await api.get_current_user()
        assert res["username"] == "testuser"

    def test_users_get_by_username_falls_back_to_ssr_html(self):
        client = MagicMock()
        client.get.side_effect = NotFoundError("Resource not found", status_code=404)
        client.get_html.return_value = self.SAMPLE_PROFILE_HTML

        api = UsersAPI(client)
        user = api.get_by_username("instagram")
        assert isinstance(user, User)
        assert user.username == "instagram"
        assert user.followers == 686000000
        assert user.pk == 25025320

    @pytest.mark.asyncio
    async def test_async_users_get_by_username_falls_back_to_ssr_html(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=NotFoundError("Resource not found", status_code=404))
        client.get_html = AsyncMock(return_value=self.SAMPLE_PROFILE_HTML)

        api = AsyncUsersAPI(client)
        user = await api.get_by_username("instagram")
        assert user.username == "instagram"
        assert user.followers == 686000000

    def test_discover_suggested_users_handles_null_chaining(self):
        from instaharvest_v2.api.discover import DiscoverAPI
        from instaharvest_v2.api.async_discover import AsyncDiscoverAPI

        client = MagicMock()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": None}}
        assert DiscoverAPI(client).get_suggested_users("25025320") == []

        aclient = MagicMock()
        aclient.post = AsyncMock(return_value={"data": {"xdt_api__v1__discover__chaining": None}})
        assert _run(AsyncDiscoverAPI(aclient).get_suggested_users("25025320")) == []
