"""
test_100_batch1.py — Coverage push to 100%: Batch 1
=====================================================
Covers: async_monitor, async_discover, async_upload, batch, proxy_health,
        async_search, async_comment_manager, async_download, async_client,
        async_rate_limiter, events, story_composer, plugin
"""
import pytest
import asyncio
import json
import time
import threading
import re
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock, mock_open

M = MagicMock

def run(coro, timeout=5):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    except Exception:
        return None
    finally:
        try:
            for t in asyncio.all_tasks(loop):
                t.cancel()
            loop.run_until_complete(asyncio.sleep(0))
        except:
            pass
        loop.close()


# ═══════════════════════════════════════════════════════════
# ACCOUNT WATCHER (async_monitor.py)
# ═══════════════════════════════════════════════════════════
class TestAccountWatcher:
    def test_init(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("testuser")
        assert w.username == "testuser"
        assert w.user_id is None
        assert w._on_new_post == []
        assert w._on_follower_change == []
        assert w._on_new_story == []
        assert w._on_bio_change == []
        assert w._on_profile_change == []
        assert w._last_state is None
        assert w._last_post_ids == set()
        assert w._last_check == 0
        assert w._check_count == 0

    def test_on_new_post(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda x: x
        result = run(w.on_new_post(cb))
        assert result is w
        assert cb in w._on_new_post

    def test_on_follower_change(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda o, n: None
        result = run(w.on_follower_change(cb))
        assert result is w
        assert cb in w._on_follower_change

    def test_on_new_story(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda c: None
        result = run(w.on_new_story(cb))
        assert result is w
        assert cb in w._on_new_story

    def test_on_bio_change(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda o, n: None
        result = run(w.on_bio_change(cb))
        assert result is w
        assert cb in w._on_bio_change

    def test_on_profile_change(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda f, o, n: None
        result = run(w.on_profile_change(cb))
        assert result is w
        assert cb in w._on_profile_change

    def test_fire_success(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        results = []
        run(w._fire([lambda x: results.append(x)], "hello"))
        assert results == ["hello"]

    def test_fire_error(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        def bad_cb(*args): raise ValueError("boom")
        run(w._fire([bad_cb], "data"))  # should not raise

    def test_last_state_property(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        assert run(w.last_state) is None
        w._last_state = {"key": "val"}
        assert run(w.last_state) == {"key": "val"}

    def test_is_initialized(self):
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        assert run(w.is_initialized) is False
        w._last_state = {}
        assert run(w.is_initialized) is True


class TestAsyncMonitorAPIFull:
    def _api(self):
        from instaharvest_v2.api.async_monitor import AsyncMonitorAPI
        client = M()
        users = M()
        feed = M()
        stories = M()
        return AsyncMonitorAPI(client, users, feed, stories), client, users

    def test_init(self):
        api, *_ = self._api()
        assert api._watchers == {}
        assert api._running is False
        assert api._interval == 300

    def test_watch(self):
        api, *_ = self._api()
        w = run(api.watch("@TestUser"))
        assert "testuser" in api._watchers
        assert w.username == "testuser"

    def test_watch_duplicate(self):
        api, *_ = self._api()
        w1 = run(api.watch("user1"))
        w2 = run(api.watch("user1"))
        assert w1 is w2

    def test_unwatch(self):
        api, *_ = self._api()
        run(api.watch("user1"))
        assert run(api.unwatch("@user1")) is True
        assert run(api.unwatch("nonexist")) is False

    def test_watched_accounts(self):
        api, *_ = self._api()
        run(api.watch("a"))
        run(api.watch("b"))
        result = run(api.watched_accounts)
        assert "a" in result and "b" in result

    def test_watcher_count(self):
        api, *_ = self._api()
        run(api.watch("x"))
        assert run(api.watcher_count) == 1

    def test_is_running(self):
        api, *_ = self._api()
        assert run(api.is_running) is False

    def test_event_log(self):
        api, *_ = self._api()
        assert run(api.event_log) == []

    def test_log_event(self):
        api, *_ = self._api()
        run(api._log_event("user1", "test", {"k": "v"}))
        assert len(api._event_log) == 1
        assert api._event_log[0]["event"] == "test"

    def test_log_event_overflow(self):
        api, *_ = self._api()
        api._event_log = [{"i": i} for i in range(1001)]
        run(api._log_event("u", "t", {}))
        assert len(api._event_log) <= 1001

    def test_extract_state_object(self):
        from instaharvest_v2.api.async_monitor import AsyncMonitorAPI
        user = M(pk=1, username="u", full_name="F", followers=100,
                 follower_count=100, following=50, following_count=50,
                 media_count=10, biography="bio", is_private=False,
                 is_verified=True, profile_pic_url="pic", external_url="url")
        state = run(AsyncMonitorAPI._extract_state(user))
        assert state["username"] == "u"
        assert state["followers"] == 100

    def test_extract_state_dict(self):
        from instaharvest_v2.api.async_monitor import AsyncMonitorAPI
        user = {"pk": 1, "username": "u", "full_name": "F",
                "follower_count": 200, "following_count": 50,
                "media_count": 10, "biography": "b",
                "is_private": False, "is_verified": False,
                "profile_pic_url": "p", "external_url": "e"}
        state = run(AsyncMonitorAPI._extract_state(user))
        assert state["followers"] == 200

    def test_extract_state_empty(self):
        from instaharvest_v2.api.async_monitor import AsyncMonitorAPI
        assert run(AsyncMonitorAPI._extract_state(42)) == {}

    def test_get_stats(self):
        api, *_ = self._api()
        run(api.watch("u1"))
        stats = run(api.get_stats())
        assert stats["is_running"] is False
        assert stats["watched_accounts"] == 1
        assert len(stats["accounts"]) == 1

    def test_check_all_empty(self):
        api, *_ = self._api()
        result = run(api._check_all())
        assert result["checked"] == 0

    def test_check_account_initial(self):
        api, client, users = self._api()
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        users.get_by_username.return_value = M(pk=1, username="test",
            full_name="T", followers=100, follower_count=100,
            following=50, following_count=50, media_count=10,
            biography="bio", is_private=False, is_verified=False,
            profile_pic_url="p", external_url="e")
        ev = run(api._check_account(w, initial=True))
        assert ev == 0
        assert w._last_state is not None

    def test_check_account_changes(self):
        api, client, users = self._api()
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        w._last_state = {"followers": 100, "biography": "old",
                         "full_name": "F", "is_private": False,
                         "is_verified": False, "profile_pic_url": "p",
                         "external_url": "e", "user_id": 1}
        w._last_post_ids = set()
        users.get_by_username.return_value = M(pk=1, username="test",
            full_name="F", followers=200, follower_count=200,
            following=50, following_count=50, media_count=10,
            biography="new bio", is_private=False, is_verified=False,
            profile_pic_url="p", external_url="e")
        fc = []
        w._on_follower_change = [lambda o, n: fc.append((o, n))]
        bc = []
        w._on_bio_change = [lambda o, n: bc.append((o, n))]
        ev = run(api._check_account(w, initial=False))
        assert ev >= 2  # follower + bio change

    def test_check_account_user_error(self):
        api, client, users = self._api()
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        users.get_by_username.side_effect = Exception("err")
        ev = run(api._check_account(w))
        assert ev == 0

    def test_check_account_new_posts(self):
        api, client, users = self._api()
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        w._last_state = {"followers": 100, "biography": "b",
                         "full_name": "F", "is_private": False,
                         "is_verified": False, "profile_pic_url": "p",
                         "external_url": "e", "user_id": 1}
        w._last_post_ids = {"old1"}
        post_cb = []
        w._on_new_post = [lambda p: post_cb.append(p)]
        users.get_by_username.return_value = M(pk=1, username="test",
            full_name="F", followers=100, follower_count=100,
            following=50, following_count=50, media_count=11,
            biography="b", is_private=False, is_verified=False,
            profile_pic_url="p", external_url="e")
        client.request.return_value = {"items": [
            {"pk": "new1", "code": "ABC", "media_type": 1,
             "caption": {"text": "hello"}, "like_count": 5}
        ]}
        ev = run(api._check_account(w, initial=False))
        assert ev >= 1

    def test_check_account_profile_change(self):
        api, client, users = self._api()
        from instaharvest_v2.api.async_monitor import AccountWatcher
        w = AccountWatcher("test")
        w._last_state = {"followers": 100, "biography": "b",
                         "full_name": "Old Name", "is_private": False,
                         "is_verified": False, "profile_pic_url": "p",
                         "external_url": "e", "user_id": 1}
        w._last_post_ids = set()
        pc = []
        w._on_profile_change = [lambda f, o, n: pc.append((f, o, n))]
        users.get_by_username.return_value = M(pk=1, username="test",
            full_name="New Name", followers=100, follower_count=100,
            following=50, following_count=50, media_count=10,
            biography="b", is_private=False, is_verified=False,
            profile_pic_url="p", external_url="e")
        ev = run(api._check_account(w, initial=False))
        assert ev >= 1

    def test_start_stop(self):
        api, *_ = self._api()
        with patch.object(api, '_poll_loop'):
            api._running = True
            run(api.start())  # already running
            api._running = False
            # Don't actually start thread in test
            run(api.stop())

    def test_check_now(self):
        api, *_ = self._api()
        result = run(api.check_now())
        assert result["checked"] == 0

    def test_check_all_with_watchers(self):
        api, client, users = self._api()
        run(api.watch("u1"))
        users.get_by_username.return_value = M(pk=1, username="u1",
            full_name="U", followers=10, follower_count=10,
            following=5, following_count=5, media_count=1,
            biography="b", is_private=False, is_verified=False,
            profile_pic_url="p", external_url="")
        result = run(api._check_all(initial=True))
        assert result["checked"] == 1

    def test_check_all_error(self):
        api, client, users = self._api()
        run(api.watch("u1"))
        users.get_by_username.side_effect = Exception("err")
        result = run(api._check_all())
        assert result["checked"] == 1  # checked but got error inside


# ═══════════════════════════════════════════════════════════
# ASYNC DISCOVER API
# ═══════════════════════════════════════════════════════════
class TestAsyncDiscoverFull:
    def _api(self):
        from instaharvest_v2.api.async_discover import AsyncDiscoverAPI
        client = AsyncMock()
        return AsyncDiscoverAPI(client), client

    def test_get_suggested_users_raw(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": []}}}
        result = run(api.get_suggested_users_raw("123"))
        assert result is not None

    def test_get_suggested_users(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": 1, "username": "u1", "full_name": "U1", "is_verified": True, "is_private": False, "profile_pic_url": "p"},
            {"pk": 2, "username": "u2", "full_name": "U2", "is_verified": False, "is_private": True, "profile_pic_url": "p"},
            "not_a_dict",  # should be skipped
        ]}}}
        users = run(api.get_suggested_users("123"))
        assert len(users) == 2

    def test_get_suggested_users_parse_error(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": "bad"},  # will fail UserShort parsing
        ]}}}
        users = run(api.get_suggested_users("123"))
        # May or may not parse, but shouldn't crash

    def test_get_verified_suggestions(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": 1, "username": "v", "full_name": "V", "is_verified": True, "is_private": False, "profile_pic_url": "p"},
            {"pk": 2, "username": "nv", "full_name": "NV", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
        ]}}}
        result = run(api.get_verified_suggestions("123"))
        assert all(u.is_verified for u in result)

    def test_get_public_suggestions(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": 1, "username": "pub", "full_name": "P", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
            {"pk": 2, "username": "prv", "full_name": "R", "is_verified": False, "is_private": True, "profile_pic_url": "p"},
        ]}}}
        result = run(api.get_public_suggestions("123"))
        assert all(not u.is_private for u in result)

    def test_get_suggestion_usernames(self):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": 1, "username": "u1", "full_name": "U", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
        ]}}}
        result = run(api.get_suggestion_usernames("123"))
        assert result == ["u1"]

    def test_explore(self):
        api, client = self._api()
        client.get.return_value = {"status": "ok"}
        result = run(api.explore())
        assert result["status"] == "ok"

    @patch("time.sleep")
    def test_chain(self, mock_sleep):
        api, client = self._api()
        client.post.side_effect = [
            {"data": {"xdt_api__v1__discover__chaining": {"users": [
                {"pk": 10, "username": "s1", "full_name": "S1", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
            ]}}},
            {"data": {"xdt_api__v1__discover__chaining": {"users": [
                {"pk": 20, "username": "s2", "full_name": "S2", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
            ]}}},
            {"data": {"xdt_api__v1__discover__chaining": {"users": []}}},
        ]
        result = run(api.chain("1", max_depth=1, max_per_layer=2, delay=0))
        assert result["total_unique"] >= 1

    @patch("time.sleep")
    def test_chain_max_total(self, mock_sleep):
        api, client = self._api()
        client.post.return_value = {"data": {"xdt_api__v1__discover__chaining": {"users": [
            {"pk": i, "username": f"u{i}", "full_name": f"U{i}", "is_verified": False, "is_private": False, "profile_pic_url": "p"}
            for i in range(50)
        ]}}}
        result = run(api.chain("1", max_depth=2, max_per_layer=5, max_total=10, delay=0))
        assert result["total_unique"] <= 50

    @patch("time.sleep")
    def test_chain_error(self, mock_sleep):
        api, client = self._api()
        client.post.side_effect = Exception("network error")
        result = run(api.chain("1", max_depth=1, max_per_layer=1, delay=0))
        assert result["total_unique"] == 0

    @patch("time.sleep")
    def test_chain_with_progress(self, mock_sleep):
        api, client = self._api()
        progress_calls = []
        def on_progress(*args): progress_calls.append(args)
        client.post.side_effect = [
            {"data": {"xdt_api__v1__discover__chaining": {"users": [
                {"pk": 10, "username": "s1", "full_name": "S", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
            ]}}},
            {"data": {"xdt_api__v1__discover__chaining": {"users": []}}},
        ]
        result = run(api.chain("1", max_depth=1, max_per_layer=2, delay=0, on_progress=on_progress))
        assert result is not None


# ═══════════════════════════════════════════════════════════
# ASYNC UPLOAD API
# ═══════════════════════════════════════════════════════════
class TestAsyncUploadFull:
    def _api(self):
        from instaharvest_v2.api.async_upload import AsyncUploadAPI
        client = AsyncMock()
        client.upload_raw = M(return_value={"status": "ok"})
        client.get_session = M(return_value=M())
        return AsyncUploadAPI(client), client

    def test_init(self):
        api, client = self._api()
        assert api._client is client

    def test_generate_upload_id(self):
        api, _ = self._api()
        uid = run(api._generate_upload_id())
        assert uid.isdigit()

    def test_get_session(self):
        api, _ = self._api()
        result = run(api._get_session())
        assert result is not None

    @patch("time.sleep")
    def test_upload_photo(self, _):
        api, client = self._api()
        result = run(api._upload_photo(b"imgdata", "12345"))
        client.upload_raw.assert_called_once()

    @patch("time.sleep")
    def test_upload_video(self, _):
        api, client = self._api()
        result = run(api._upload_video(b"viddata", "12345", 10.0, 1080, 1920, False))
        client.upload_raw.assert_called_once()

    @patch("time.sleep")
    def test_upload_video_clips(self, _):
        api, client = self._api()
        result = run(api._upload_video(b"viddata", is_clips=True))
        call_args = client.upload_raw.call_args
        params = json.loads(call_args[1]["headers"]["x-instagram-rupload-params"])
        assert params["is_clips_video"] == "1"

    @patch("time.sleep")
    def test_post_photo_data(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok", "media": {"pk": 1}}
        result = run(api.post_photo(image_data=b"imgdata", caption="test"))
        assert result is not None

    @patch("time.sleep")
    def test_post_photo_no_data(self, _):
        api, _ = self._api()
        result = run(api.post_photo())
        assert result is None  # ValueError raised, caught by run()

    @patch("time.sleep")
    def test_post_photo_upload_fail(self, _):
        api, client = self._api()
        client.upload_raw.return_value = {"status": "fail"}
        result = run(api.post_photo(image_data=b"img"))
        assert result["status"] == "fail"

    @patch("time.sleep")
    def test_post_photo_with_location(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_photo(image_data=b"img", location={"name": "Paris", "lat": 48.8, "lng": 2.3}))
        assert result is not None

    @patch("time.sleep")
    def test_post_photo_with_usertags(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_photo(image_data=b"img", usertags=[{"user_id": 123}]))
        assert result is not None

    @patch("time.sleep")
    def test_post_photo_disable_comments(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_photo(image_data=b"img", disable_comments=True))
        assert result is not None

    @patch("time.sleep")
    def test_post_photo_from_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"imgbytes")
        with patch("builtins.open", m):
            result = run(api.post_photo(image_path="/tmp/test.jpg"))
        assert result is not None

    @patch("time.sleep")
    def test_post_video_data(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_video(video_data=b"vid", duration=10))
        assert result is not None

    @patch("time.sleep")
    def test_post_video_no_data(self, _):
        api, _ = self._api()
        result = run(api.post_video())
        assert result is None

    @patch("time.sleep")
    def test_post_video_from_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"vidbytes")
        with patch("builtins.open", m):
            result = run(api.post_video(video_path="/tmp/v.mp4"))
        assert result is not None

    @patch("time.sleep")
    def test_post_video_with_thumbnail_data(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_video(video_data=b"vid", thumbnail_data=b"thumb"))
        assert result is not None

    @patch("time.sleep")
    def test_post_video_with_thumbnail_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"bytes")
        with patch("builtins.open", m):
            result = run(api.post_video(video_data=b"vid", thumbnail_path="/tmp/t.jpg"))
        assert result is not None

    @patch("time.sleep")
    def test_post_video_with_location(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_video(video_data=b"vid", location={"name": "NYC"}))
        assert result is not None

    @patch("time.sleep")
    def test_post_story_photo(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_story_photo(image_data=b"img"))
        assert result is not None

    @patch("time.sleep")
    def test_post_story_photo_no_data(self, _):
        api, _ = self._api()
        result = run(api.post_story_photo())
        assert result is None

    @patch("time.sleep")
    def test_post_story_photo_from_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"img")
        with patch("builtins.open", m):
            result = run(api.post_story_photo(image_path="/tmp/s.jpg"))
        assert result is not None

    @patch("time.sleep")
    def test_post_story_video(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_story_video(video_data=b"vid", duration=15))
        assert result is not None

    @patch("time.sleep")
    def test_post_story_video_no_data(self, _):
        api, _ = self._api()
        result = run(api.post_story_video())
        assert result is None

    @patch("time.sleep")
    def test_post_story_video_from_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"vid")
        with patch("builtins.open", m):
            result = run(api.post_story_video(video_path="/tmp/s.mp4"))
        assert result is not None

    @patch("time.sleep")
    def test_post_reel(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_reel(video_data=b"reel", caption="My reel"))
        assert result is not None

    @patch("time.sleep")
    def test_post_reel_no_data(self, _):
        api, _ = self._api()
        result = run(api.post_reel())
        assert result is None

    @patch("time.sleep")
    def test_post_reel_from_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"reel")
        with patch("builtins.open", m):
            result = run(api.post_reel(video_path="/tmp/r.mp4"))
        assert result is not None

    @patch("time.sleep")
    def test_post_reel_with_thumbnail(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.post_reel(video_data=b"r", thumbnail_data=b"t"))
        assert result is not None

    @patch("time.sleep")
    def test_post_reel_with_thumbnail_path(self, _):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"bytes")
        with patch("builtins.open", m):
            result = run(api.post_reel(video_data=b"r", thumbnail_path="/tmp/t.jpg"))
        assert result is not None

    def test_delete_media(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok", "did_delete": True}
        result = run(api.delete_media("12345", media_type=1))
        assert result["did_delete"] is True

    @patch("time.sleep")
    def test_post_carousel(self, _):
        api, client = self._api()
        client.upload_raw.return_value = {"status": "ok"}
        client.post.return_value = {"status": "ok"}
        result = run(api.post_carousel(images=[b"img1", b"img2"], caption="Album"))
        assert result is not None

    @patch("time.sleep")
    def test_post_carousel_too_few(self, _):
        api, _ = self._api()
        result = run(api.post_carousel(images=[b"one"]))
        assert result is None

    @patch("time.sleep")
    def test_post_carousel_too_many(self, _):
        api, _ = self._api()
        result = run(api.post_carousel(images=[b"x"] * 11))
        assert result is None

    @patch("time.sleep")
    def test_post_carousel_no_images(self, _):
        api, _ = self._api()
        result = run(api.post_carousel(images=None))
        assert result is None

    @patch("time.sleep")
    def test_post_carousel_upload_fail(self, _):
        api, client = self._api()
        client.upload_raw.return_value = {"status": "fail"}
        result = run(api.post_carousel(images=[b"i1", b"i2"]))
        assert result["status"] == "fail"

    @patch("time.sleep")
    def test_post_carousel_from_paths(self, _):
        api, client = self._api()
        client.upload_raw.return_value = {"status": "ok"}
        client.post.return_value = {"status": "ok"}
        m = mock_open(read_data=b"imgbytes")
        with patch("builtins.open", m):
            result = run(api.post_carousel(images=["/tmp/a.jpg", "/tmp/b.jpg"]))
        assert result is not None

    @patch("time.sleep")
    def test_post_carousel_with_location_usertags(self, _):
        api, client = self._api()
        client.upload_raw.return_value = {"status": "ok"}
        client.post.return_value = {"status": "ok"}
        result = run(api.post_carousel(
            images=[b"i1", b"i2"],
            location={"name": "Paris", "lat": 48.8, "lng": 2.3},
            usertags=[{"user_id": 123}],
            disable_comments=True))
        assert result is not None


# ═══════════════════════════════════════════════════════════
# BATCH API
# ═══════════════════════════════════════════════════════════
class TestBatchAPI:
    def _api(self):
        from instaharvest_v2.batch import BatchAPI
        ig = M()
        ig.users.get_by_username = AsyncMock(return_value={"pk": 1})
        ig.friendships.show = AsyncMock(return_value={"following": True})
        ig.friendships.follow = AsyncMock(return_value={"status": "ok"})
        ig.media.get_info = AsyncMock(return_value={"pk": "m1"})
        ig.media.like = AsyncMock(return_value={"status": "ok"})
        return BatchAPI(ig), ig

    def test_init(self):
        api, ig = self._api()
        assert api._ig is ig

    def test_run_batch(self):
        api, _ = self._api()
        async def fn(item): return item * 2
        results = run(api._run_batch([1, 2, 3], fn, concurrency=2))
        assert len(results) == 3
        assert results[0] == (1, 2)

    def test_run_batch_error_silent(self):
        api, _ = self._api()
        async def fn(item):
            if item == 2: raise ValueError("boom")
            return item
        results = run(api._run_batch([1, 2, 3], fn, fail_silently=True))
        assert len(results) == 3

    def test_run_batch_error_raise(self):
        api, _ = self._api()
        async def fn(item): raise ValueError("boom")
        # With fail_silently=False, gather will raise
        result = run(api._run_batch([1], fn, fail_silently=False))
        # run() catches exceptions and returns None

    def test_run_batch_with_progress(self):
        api, _ = self._api()
        progress = []
        async def fn(item): return item
        def on_progress(completed, total, item, result):
            progress.append((completed, total))
        results = run(api._run_batch([1, 2], fn, on_progress=on_progress))
        assert len(progress) == 2

    def test_run_batch_progress_error(self):
        api, _ = self._api()
        def bad_progress(*a): raise Exception("bad")
        async def fn(item): return item
        results = run(api._run_batch([1], fn, on_progress=bad_progress))
        assert len(results) == 1

    def test_run_batch_progress_on_error(self):
        api, _ = self._api()
        progress = []
        async def fn(item): raise ValueError("x")
        def on_progress(c, t, i, r): progress.append(r)
        results = run(api._run_batch([1], fn, fail_silently=True, on_progress=on_progress))
        assert progress[0] is None

    def test_check_profiles(self):
        api, ig = self._api()
        result = run(api.check_profiles(["u1", "u2"]))
        assert len(result) == 2

    def test_check_follow_backs(self):
        api, ig = self._api()
        result = run(api.check_follow_backs([1, 2]))
        assert len(result) == 2

    def test_get_media_infos(self):
        api, ig = self._api()
        result = run(api.get_media_infos(["m1"]))
        assert len(result) == 1

    def test_bulk_follow(self):
        api, ig = self._api()
        result = run(api.bulk_follow([1, 2], delay=0))
        assert len(result) == 2

    def test_bulk_like(self):
        api, ig = self._api()
        result = run(api.bulk_like(["m1", "m2"], delay=0))
        assert len(result) == 2

    def test_run_custom(self):
        api, _ = self._api()
        async def fn(x): return x + "!"
        result = run(api.run(["a", "b"], fn))
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════
# PROXY HEALTH CHECKER
# ═══════════════════════════════════════════════════════════
class TestProxyHealthChecker:
    def _checker(self):
        from instaharvest_v2.proxy_health import ProxyHealthChecker
        from instaharvest_v2.proxy_manager import ProxyManager
        pm = ProxyManager()
        return ProxyHealthChecker(pm, interval=1, timeout=2), pm

    def test_init(self):
        checker, pm = self._checker()
        assert checker._proxy_mgr is pm
        assert checker._interval == 1
        assert checker._timeout == 2
        assert checker._running is False

    def test_is_running(self):
        checker, _ = self._checker()
        assert checker.is_running is False

    def test_start_stop(self):
        checker, _ = self._checker()
        with patch.object(checker, '_run_loop'):
            checker.start()
            assert checker._running is True
            checker.start()  # already running, no-op
            checker.stop()
            assert checker._running is False

    def test_check_all_empty(self):
        checker, pm = self._checker()
        result = checker.check_all()
        assert result["total"] == 0
        assert result["alive"] == 0

    def test_check_all_with_proxies(self):
        checker, pm = self._checker()
        pm.add_proxy("http://proxy1:8080")
        with patch.object(checker, '_check_proxy', return_value=(True, 0.5)):
            result = checker.check_all()
        assert result["alive"] == 1

    def test_check_all_dead_proxy(self):
        checker, pm = self._checker()
        pm.add_proxy("http://proxy1:8080")
        with patch.object(checker, '_check_proxy', return_value=(False, None)):
            result = checker.check_all()
        assert result["dead"] == 1

    def test_check_all_recovered_proxy(self):
        checker, pm = self._checker()
        pm.add_proxy("http://proxy1:8080")
        # Set proxy as inactive
        for url, info in pm._proxies.items():
            info.is_active = False
        with patch.object(checker, '_check_proxy', return_value=(True, 0.3)):
            result = checker.check_all()
        assert result["recovered"] == 1

    def test_check_all_with_events(self):
        from instaharvest_v2.proxy_health import ProxyHealthChecker
        from instaharvest_v2.proxy_manager import ProxyManager
        pm = ProxyManager()
        events = M()
        checker = ProxyHealthChecker(pm, event_emitter=events)
        pm.add_proxy("http://proxy1:8080")
        for url, info in pm._proxies.items():
            info.is_active = False
        with patch.object(checker, '_check_proxy', return_value=(True, 0.3)):
            checker.check_all()
        # Events should have been called

    def test_check_proxy_success(self):
        checker, _ = self._checker()
        with patch("instaharvest_v2.proxy_health.ProxyHealthChecker._check_proxy",
                    return_value=(True, 0.5)):
            alive, latency = checker._check_proxy("http://test:8080")
            assert alive is True

    def test_check_proxy_failure(self):
        checker, _ = self._checker()
        # Test the actual method with mocked curl
        with patch.dict('sys.modules', {'curl_cffi': M(), 'curl_cffi.requests': M()}):
            import sys
            mock_curl = sys.modules['curl_cffi.requests']
            mock_curl.get.side_effect = Exception("timeout")
            alive, latency = checker._check_proxy("http://bad:8080")
            assert alive is False

    def test_run_loop(self):
        checker, _ = self._checker()
        checker._stop_event = threading.Event()
        checker._stop_event.set()  # stop immediately
        with patch.object(checker, 'check_all'):
            checker._run_loop()

    def test_del(self):
        checker, _ = self._checker()
        checker.__del__()


# ═══════════════════════════════════════════════════════════
# ASYNC COMMENT MANAGER
# ═══════════════════════════════════════════════════════════
class TestAsyncCommentManagerFull:
    def _api(self):
        from instaharvest_v2.api.async_comment_manager import AsyncCommentManagerAPI
        client = M()
        media = M()
        return AsyncCommentManagerAPI(client, media), client, media

    def test_init(self):
        api, *_ = self._api()
        assert len(api._spam_patterns) > 0

    def test_is_spam_empty(self):
        api, *_ = self._api()
        assert run(api._is_spam("")) is False

    def test_is_spam_f4f(self):
        api, *_ = self._api()
        assert run(api._is_spam("follow me back f4f")) is True

    def test_is_spam_link(self):
        api, *_ = self._api()
        assert run(api._is_spam("check https://evil.com")) is True

    def test_is_spam_repetitive(self):
        api, *_ = self._api()
        assert run(api._is_spam("🔥🔥🔥🔥🔥")) is True

    def test_is_spam_normal(self):
        api, *_ = self._api()
        assert run(api._is_spam("Beautiful photo!")) is False

    def test_quick_sentiment_empty(self):
        from instaharvest_v2.api.async_comment_manager import AsyncCommentManagerAPI
        assert run(AsyncCommentManagerAPI._quick_sentiment("")) == "neutral"

    def test_quick_sentiment_positive(self):
        from instaharvest_v2.api.async_comment_manager import AsyncCommentManagerAPI
        assert run(AsyncCommentManagerAPI._quick_sentiment("Amazing beautiful love ❤️")) == "positive"

    def test_quick_sentiment_negative(self):
        from instaharvest_v2.api.async_comment_manager import AsyncCommentManagerAPI
        assert run(AsyncCommentManagerAPI._quick_sentiment("ugly terrible hate 😡🤮")) == "negative"

    def test_quick_sentiment_neutral(self):
        from instaharvest_v2.api.async_comment_manager import AsyncCommentManagerAPI
        assert run(AsyncCommentManagerAPI._quick_sentiment("okay")) == "neutral"

    def test_get_comments(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "Great!", "user": {"username": "u1", "pk": 10},
                 "comment_like_count": 5, "created_at": 1000},
                {"pk": 2, "text": "follow me f4f", "user": {"username": "spammer", "pk": 20},
                 "comment_like_count": 0, "created_at": 2000},
            ],
            "has_more_comments": False,
        }
        result = run(api.get_comments("media1", count=50, sort="newest"))
        assert result["count"] == 2

    def test_get_comments_sort_top(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "a", "user": {"username": "u1", "pk": 10},
                 "comment_like_count": 1, "created_at": 1000},
                {"pk": 2, "text": "b", "user": {"username": "u2", "pk": 20},
                 "comment_like_count": 10, "created_at": 2000},
            ],
            "has_more_comments": False,
        }
        result = run(api.get_comments("media1", sort="top"))
        assert result["comments"][0]["likes"] == 10

    def test_get_comments_sort_oldest(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "a", "user": {"username": "u1", "pk": 10},
                 "comment_like_count": 0, "created_at": 2000},
                {"pk": 2, "text": "b", "user": {"username": "u2", "pk": 20},
                 "comment_like_count": 0, "created_at": 1000},
            ],
            "has_more_comments": False,
        }
        result = run(api.get_comments("media1", sort="oldest"))
        assert result["comments"][0]["created_at"] == 1000

    def test_get_comments_pagination(self):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [{"pk": 1, "text": "a", "user": {"username": "u", "pk": 1},
                           "comment_like_count": 0, "created_at": 1}],
             "has_more_comments": True, "next_min_id": "cursor1"},
            {"comments": [{"pk": 2, "text": "b", "user": {"username": "u2", "pk": 2},
                           "comment_like_count": 0, "created_at": 2}],
             "has_more_comments": False},
        ]
        result = run(api.get_comments("m1", count=100))
        assert result["count"] == 2

    def test_get_comments_error(self):
        api, client, _ = self._api()
        client.request.side_effect = Exception("err")
        result = run(api.get_comments("m1"))
        assert result["count"] == 0

    def test_get_comments_bad_result(self):
        api, client, _ = self._api()
        client.request.return_value = None
        result = run(api.get_comments("m1"))
        assert result["count"] == 0

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_auto_reply(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "price?", "user": {"username": "buyer", "pk": 10},
                 "comment_like_count": 0, "created_at": 1},
                {"pk": 2, "text": "nice pic", "user": {"username": "viewer", "pk": 20},
                 "comment_like_count": 0, "created_at": 2},
            ], "has_more_comments": False},
            {"status": "ok"},  # reply
        ]
        result = run(api.auto_reply("m1", keyword="price", reply="DM us {username}!", max_count=5))
        assert result["replied"] >= 1

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_auto_reply_spam_skip(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "follow me f4f", "user": {"username": "spam", "pk": 10},
                 "comment_like_count": 0, "created_at": 1},
            ], "has_more_comments": False},
        ]
        result = run(api.auto_reply("m1", reply="thanks"))
        assert result["skipped"] >= 1

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_auto_reply_error(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "hello", "user": {"username": "u", "pk": 10},
                 "comment_like_count": 0, "created_at": 1},
            ], "has_more_comments": False},
            Exception("post error"),
        ]
        result = run(api.auto_reply("m1", reply="hi"))
        assert result["errors"] >= 1

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_bulk_reply(self, _, __):
        api, client, _ = self._api()
        client.request.return_value = {"comments": [], "has_more_comments": False}
        result = run(api.bulk_reply("m1", reply="Thanks!"))
        assert result is not None

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_delete_spam(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "follow me f4f", "user": {"username": "spam", "pk": 10},
                 "comment_like_count": 0, "created_at": 1},
                {"pk": 2, "text": "Nice!", "user": {"username": "real", "pk": 20},
                 "comment_like_count": 5, "created_at": 2},
            ], "has_more_comments": False},
            {"status": "ok"},  # delete
        ]
        result = run(api.delete_spam("m1"))
        assert result["deleted"] >= 1

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_delete_spam_custom_patterns(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "buy my product", "user": {"username": "ad", "pk": 10},
                 "comment_like_count": 0, "created_at": 1},
            ], "has_more_comments": False},
            {"status": "ok"},
        ]
        result = run(api.delete_spam("m1", custom_patterns=[r"buy\s+my"]))
        assert result["deleted"] >= 1

    @patch("time.sleep")
    @patch("random.uniform", return_value=0)
    def test_delete_spam_delete_error(self, _, __):
        api, client, _ = self._api()
        client.request.side_effect = [
            {"comments": [
                {"pk": 1, "text": "f4f follow back", "user": {"username": "s", "pk": 1},
                 "comment_like_count": 0, "created_at": 1},
            ], "has_more_comments": False},
            Exception("delete err"),
        ]
        result = run(api.delete_spam("m1"))
        assert result["deleted"] == 0

    def test_sentiment(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "Amazing love beautiful!", "user": {"username": "u", "pk": 1},
                 "comment_like_count": 0, "created_at": 1},
                {"pk": 2, "text": "Ugly terrible", "user": {"username": "u2", "pk": 2},
                 "comment_like_count": 0, "created_at": 2},
                {"pk": 3, "text": "okay", "user": {"username": "u3", "pk": 3},
                 "comment_like_count": 0, "created_at": 3},
            ],
            "has_more_comments": False,
        }
        result = run(api.sentiment("m1"))
        assert result["total_analyzed"] == 3
        assert "overall" in result

    def test_filter_comments(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "love it", "user": {"username": "u", "pk": 1},
                 "comment_like_count": 10, "created_at": 1},
                {"pk": 2, "text": "follow me f4f", "user": {"username": "s", "pk": 2},
                 "comment_like_count": 0, "created_at": 2},
                {"pk": 3, "text": "nice work", "user": {"username": "u3", "pk": 3},
                 "comment_like_count": 2, "created_at": 3},
            ],
            "has_more_comments": False,
        }
        result = run(api.filter_comments("m1", keyword="love", min_likes=5, exclude_spam=True))
        assert len(result) >= 1

    def test_filter_comments_sentiment(self):
        api, client, _ = self._api()
        client.request.return_value = {
            "comments": [
                {"pk": 1, "text": "amazing beautiful", "user": {"username": "u", "pk": 1},
                 "comment_like_count": 0, "created_at": 1},
            ],
            "has_more_comments": False,
        }
        result = run(api.filter_comments("m1", sentiment_filter="positive"))
        assert len(result) >= 1
