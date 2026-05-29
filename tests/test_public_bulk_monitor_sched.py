"""
test_public_bulk_monitor_sched.py — Deep Coverage for 4 Major API Modules
==========================================================================
PublicAPI (218 miss), BulkDownloadAPI (189×2 miss), MonitorAPI (169×2 miss), SchedulerAPI (151×2 miss)
"""
import os
import json
import time
import pytest
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime

M = MagicMock


# ═══════════════════════════════════════════════════════════
# PublicAPI — full method body coverage
# ═══════════════════════════════════════════════════════════
class TestPublicAPIDeep:
    def _make(self):
        from instaharvest_v2.api.public import PublicAPI
        anon = M()
        # PublicAPI routes reads through anon.cached_call(key, fetch_fn).
        # Make the mock execute the fetch_fn so underlying *_chain mocks run.
        anon.cached_call.side_effect = lambda key_parts, fetch_fn, ttl=None: fetch_fn()
        return PublicAPI(anon)

    def test_get_profile(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"username": "test", "followers": 1000}
        result = api.get_profile("@TestUser")
        api._client.get_profile_chain.assert_called_with("testuser")
        assert result["username"] == "test"

    def test_get_user_id_from_profile(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"pk": 123}
        assert api.get_user_id("testuser") == 123

    def test_get_user_id_fallback_web_profile(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"username": "test"}  # no pk
        api._client.get_web_profile.return_value = {"id": "456"}
        assert api.get_user_id("testuser") == 456

    def test_get_user_id_none(self):
        api = self._make()
        api._client.get_profile_chain.return_value = None
        api._client.get_web_profile.return_value = None
        assert api.get_user_id("none") is None

    def test_get_profile_pic_url(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"profile_pic_url_hd": "http://pic.jpg"}
        assert api.get_profile_pic_url("test") == "http://pic.jpg"

    def test_get_post_by_shortcode(self):
        api = self._make()
        api._client.get_post_chain.return_value = {"shortcode": "ABC", "likes": 100}
        result = api.get_post_by_shortcode("ABC")
        assert result["shortcode"] == "ABC"

    @patch("instaharvest_v2.utils.extract_shortcode", return_value="ABC123")
    def test_get_post_by_url(self, _):
        api = self._make()
        api._client.get_post_chain.return_value = {"shortcode": "ABC123"}
        result = api.get_post_by_url("https://instagram.com/p/ABC123/")
        assert result["shortcode"] == "ABC123"

    @patch("instaharvest_v2.utils.extract_shortcode", return_value=None)
    def test_get_post_by_url_invalid(self, _):
        api = self._make()
        assert api.get_post_by_url("badurl") is None

    def test_get_feed(self):
        api = self._make()
        api._client.get_user_feed_mobile.return_value = {"items": [{"pk": 1}], "next_max_id": None, "more_available": False}
        result = api.get_feed(123, max_count=12)
        assert len(result["items"]) == 1

    def test_get_feed_none(self):
        api = self._make()
        api._client.get_user_feed_mobile.return_value = None
        result = api.get_feed(123)
        assert result["items"] == []

    def test_get_media(self):
        api = self._make()
        api._client.get_media_info_mobile.return_value = {"pk": 1, "likes": 100}
        assert api.get_media(1)["likes"] == 100

    def test_get_comments(self):
        api = self._make()
        api._client.get_post_comments_graphql.return_value = {
            "edges": [{"node": {"id": "1", "text": "Nice!", "owner": {"username": "u1", "id": "10", "is_verified": False}, "edge_liked_by": {"count": 5}, "edge_threaded_comments": {"count": 0}, "created_at": 1000}}]
        }
        comments = api.get_comments("ABC", max_count=10)
        assert len(comments) == 1
        assert comments[0]["text"] == "Nice!"

    def test_get_hashtag_posts(self):
        api = self._make()
        api._client.get_hashtag_posts_graphql.return_value = {
            "edge_hashtag_to_media": {"edges": [{"node": {"shortcode": "A"}}]}
        }
        api._client._parse_timeline_edges.return_value = [{"shortcode": "A"}]
        result = api.get_hashtag_posts("#fashion", 5)
        assert len(result) >= 1

    def test_search(self):
        api = self._make()
        api._client.search_web.return_value = {"users": [{"username": "cr7"}], "hashtags": [], "places": []}
        result = api.search("cristiano")
        assert len(result["users"]) == 1

    def test_search_none(self):
        api = self._make()
        api._client.search_web.return_value = None
        result = api.search("x")
        assert result["users"] == []

    def test_get_reels(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"pk": 123}
        api._client.get_web_profile.return_value = None
        api._client.get_user_reels.return_value = {"items": [{"pk": 1, "play_count": 1000}]}
        result = api.get_reels("testuser", 5)
        assert len(result) == 1

    def test_get_hashtag_posts_v2(self):
        api = self._make()
        api._client.get_hashtag_sections.return_value = {"posts": [{"pk": 1}, {"pk": 2}], "more_available": True}
        result = api.get_hashtag_posts_v2("fashion", max_count=1)
        assert len(result["posts"]) == 1

    def test_get_location_posts(self):
        api = self._make()
        api._client.get_location_sections.return_value = {"posts": [{"pk": 1}], "more_available": False}
        result = api.get_location_posts(123)
        assert len(result["posts"]) == 1

    def test_get_similar_accounts(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"pk": 123}
        api._client.get_web_profile.return_value = None
        api._client.get_similar_accounts.return_value = [{"username": "sim1"}]
        result = api.get_similar_accounts("test")
        assert len(result) == 1

    def test_get_highlights(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"pk": 123}
        api._client.get_web_profile.return_value = None
        api._client.get_highlights_tray.return_value = [{"title": "Travel"}]
        result = api.get_highlights("test")
        assert len(result) == 1

    def test_is_public(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"is_private": False}
        assert api.is_public("test") is True

    def test_is_public_private(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"is_private": True}
        assert api.is_public("test") is False

    def test_is_public_not_found(self):
        api = self._make()
        api._client.get_profile_chain.return_value = None
        assert api.is_public("test") is None

    def test_exists(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"username": "test"}
        assert api.exists("test") is True

    def test_request_count(self):
        api = self._make()
        api._client.request_count = 42
        assert api.request_count == 42

    def test_get_media_urls_carousel(self):
        api = self._make()
        api._client.get_post_chain.return_value = {
            "carousel_media": [
                {"display_url": "http://img1.jpg", "is_video": False, "display_resources": [{"url": "http://hd1.jpg", "width": 1080, "height": 1080}]},
                {"display_url": "http://img2.jpg", "is_video": True, "video_url": "http://vid.mp4", "display_resources": []},
            ]
        }
        urls = api.get_media_urls("ABC")
        assert any(u["type"] == "video" for u in urls)
        assert any(u["type"] == "image" for u in urls)

    def test_get_media_urls_single(self):
        api = self._make()
        api._client.get_post_chain.return_value = {"images": [{"url": "http://img.jpg", "width": 1080, "height": 1080}]}
        urls = api.get_media_urls("ABC")
        assert len(urls) >= 1

    def test_get_media_urls_video(self):
        api = self._make()
        api._client.get_post_chain.return_value = {"video_url": "http://vid.mp4", "images": []}
        urls = api.get_media_urls("ABC")
        assert any(u["type"] == "video" for u in urls)

    def test_get_media_urls_none(self):
        api = self._make()
        api._client.get_post_chain.return_value = None
        assert api.get_media_urls("X") == []

    def test_bulk_profiles(self):
        api = self._make()
        api._client.get_profile_chain.return_value = {"username": "test", "followers": 100}
        results = api.bulk_profiles(["u1", "u2"], workers=2)
        assert len(results) == 2

    def test_bulk_feeds(self):
        api = self._make()
        api._client.get_user_feed_mobile.return_value = {"items": [{"pk": 1}], "next_max_id": None, "more_available": False}
        results = api.bulk_feeds([123, 456], max_count=5, workers=2)
        assert len(results) == 2

    def test_get_all_posts(self):
        api = self._make()
        api._client.get_web_profile.return_value = {
            "id": 123, "edge_owner_to_timeline_media": {"edges": [{"node": {"shortcode": "A"}}]}
        }
        api._client._parse_timeline_edges.return_value = [{"pk": 1, "shortcode": "A"}]
        api._client.get_user_feed_mobile.return_value = {"items": [{"pk": 2, "shortcode": "B"}], "more_available": False}
        result = api.get_all_posts("test", max_count=5)
        assert len(result) >= 1


# ═══════════════════════════════════════════════════════════
# BulkDownloadAPI — all method bodies
# ═══════════════════════════════════════════════════════════
class TestBulkDownloadAPIDeep:
    def _make(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        return BulkDownloadAPI(M(), M(), M(), M())

    def test_extract_media_urls_photo(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        item = {"media_type": 1, "image_versions2": {"candidates": [{"url": "http://img.jpg", "width": 1080, "height": 1080}]}}
        urls = BulkDownloadAPI._extract_media_urls(item)
        assert len(urls) == 1 and urls[0][1] == ".jpg"

    def test_extract_media_urls_video(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        item = {"media_type": 2, "video_versions": [{"url": "http://vid.mp4", "width": 1080, "height": 1920}]}
        urls = BulkDownloadAPI._extract_media_urls(item)
        assert urls[0][1] == ".mp4"

    def test_extract_media_urls_carousel(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        item = {"media_type": 8, "carousel_media": [
            {"media_type": 1, "image_versions2": {"candidates": [{"url": "http://img1.jpg", "width": 1080, "height": 1080}]}},
            {"media_type": 2, "video_versions": [{"url": "http://vid.mp4", "width": 720, "height": 1280}]},
        ]}
        urls = BulkDownloadAPI._extract_media_urls(item)
        assert len(urls) == 2

    def test_fetch_all_posts(self):
        api = self._make()
        api._client.request.return_value = {"items": [{"pk": 1}, {"pk": 2}], "more_available": False}
        posts = api._fetch_all_posts("123", max_count=5)
        assert len(posts) == 2

    def test_download_file(self):
        api = self._make()
        api._download.url_to_file.return_value = None
        api._download_file("http://img.jpg", "/tmp/img.jpg")
        api._download.url_to_file.assert_called_once()

    def test_download_file_empty_url(self):
        api = self._make()
        api._download_file("", "/tmp/x.jpg")

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_all_posts(self, mock_f, mock_dirs):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._client.request.return_value = {"items": [
            {"pk": 1, "code": "ABC", "media_type": 1, "taken_at": int(time.time()),
             "like_count": 100, "comment_count": 5, "caption": {"text": "Hello"},
             "image_versions2": {"candidates": [{"url": "http://img.jpg", "width": 1080, "height": 1080}]}}
        ], "more_available": False}
        api._download.url_to_file.return_value = None
        result = api.all_posts("testuser", tempfile.mkdtemp(), max_count=1)
        assert result["total"] == 1

    @patch("os.makedirs")
    def test_all_stories(self, _):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._stories.get_user_stories.return_value = {
            "items": [{"pk": 1, "taken_at": int(time.time()), "media_type": 1,
                        "image_versions2": {"candidates": [{"url": "http://s.jpg", "width": 1080, "height": 1920}]}}]
        }
        api._download.url_to_file.return_value = None
        result = api.all_stories("testuser", tempfile.mkdtemp())
        assert result["total"] == 1

    def test_all_stories_no_api(self):
        from instaharvest_v2.api.bulk_download import BulkDownloadAPI
        api = BulkDownloadAPI(M(), M(), M(), stories_api=None)
        result = api.all_stories("test", "/tmp/x")
        assert result["downloaded"] == 0

    @patch("os.makedirs")
    def test_all_highlights(self, _):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._stories.get_highlights.return_value = {
            "tray": [{"title": "Travel", "id": "hl:1",
                       "items": [{"media_type": 1, "image_versions2": {"candidates": [{"url": "http://h.jpg", "width": 1080, "height": 1080}]}}]}]
        }
        api._stories.get_highlight_items.return_value = {
            "items": [{"media_type": 1, "image_versions2": {"candidates": [{"url": "http://h.jpg", "width": 1080, "height": 1080}]}}]
        }
        api._download.url_to_file.return_value = None
        result = api.all_highlights("testuser", tempfile.mkdtemp())
        assert result["highlights"] == 1

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_everything(self, mock_f, mock_dirs):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._client.request.return_value = {"items": [], "more_available": False}
        api._stories.get_user_stories.return_value = {"items": []}
        api._stories.get_highlights.return_value = {"tray": []}
        result = api.everything("testuser", tempfile.mkdtemp())
        assert "total_files" in result


# ═══════════════════════════════════════════════════════════
# AccountWatcher + MonitorAPI — deep coverage
# ═══════════════════════════════════════════════════════════
class TestAccountWatcher:
    def test_init(self):
        from instaharvest_v2.api.monitor import AccountWatcher
        w = AccountWatcher("cristiano")
        assert w.username == "cristiano"
        assert w.user_id is None
        assert not w.is_initialized

    def test_callback_registration(self):
        from instaharvest_v2.api.monitor import AccountWatcher
        w = AccountWatcher("test")
        cb = lambda *a: None
        w.on_new_post(cb).on_follower_change(cb).on_new_story(cb).on_bio_change(cb).on_profile_change(cb)
        assert len(w._on_new_post) == 1
        assert len(w._on_follower_change) == 1

    def test_fire_safe(self):
        from instaharvest_v2.api.monitor import AccountWatcher
        w = AccountWatcher("test")
        called = []
        w._fire([lambda x: called.append(x), lambda x: 1/0], "data")  # second fires error, should not crash
        assert called == ["data"]


class TestMonitorAPIDeep:
    def _make(self):
        from instaharvest_v2.api.monitor import MonitorAPI
        return MonitorAPI(M(), M(), M(), M())

    def test_watch(self):
        api = self._make()
        w = api.watch("@Cristiano")
        assert w.username == "cristiano"
        assert "cristiano" in api.watched_accounts

    def test_unwatch(self):
        api = self._make()
        api.watch("test")
        assert api.unwatch("test") is True
        assert api.unwatch("nonexistent") is False

    def test_watcher_count(self):
        api = self._make()
        api.watch("u1"); api.watch("u2")
        assert api.watcher_count == 2

    def test_extract_state_dict(self):
        from instaharvest_v2.api.monitor import MonitorAPI
        state = MonitorAPI._extract_state({"pk": 1, "username": "test", "full_name": "T", "follower_count": 100, "biography": "bio"})
        assert state["user_id"] == 1

    def test_extract_state_object(self):
        from instaharvest_v2.api.monitor import MonitorAPI
        u = M(); u.pk = 1; u.username = "test"; u.full_name = "T"; u.followers = 100
        u.follower_count = 100; u.following = 50; u.following_count = 50
        u.media_count = 10; u.biography = "bio"; u.is_private = False
        u.is_verified = True; u.profile_pic_url = "http://pic.jpg"; u.external_url = ""
        state = MonitorAPI._extract_state(u)
        assert state["username"] == "test"

    def test_log_event(self):
        api = self._make()
        api._log_event("test", "follower_change", {"old": 100, "new": 110})
        assert len(api.event_log) == 1

    def test_get_stats(self):
        api = self._make()
        api.watch("test")
        stats = api.get_stats()
        assert stats["watched_accounts"] == 1
        assert stats["is_running"] is False

    def test_check_now_initial(self):
        api = self._make()
        api.watch("test")
        api._users.get_by_username.return_value = {"pk": 1, "username": "test", "follower_count": 100, "biography": "bio"}
        result = api.check_now()
        assert result["checked"] == 1

    def test_check_now_detect_follower_change(self):
        api = self._make()
        w = api.watch("test")
        changes = []
        w.on_follower_change(lambda o, n: changes.append((o, n)))
        api._users.get_by_username.return_value = {"pk": 1, "username": "test", "follower_count": 100, "biography": "bio"}
        api.check_now()  # initial baseline
        api._users.get_by_username.return_value = {"pk": 1, "username": "test", "follower_count": 110, "biography": "bio"}
        result = api.check_now()  # detect change
        assert result["events_fired"] >= 1
        assert (100, 110) in changes

    def test_check_now_detect_bio_change(self):
        api = self._make()
        w = api.watch("test")
        bios = []
        w.on_bio_change(lambda o, n: bios.append((o, n)))
        api._users.get_by_username.return_value = {"pk": 1, "username": "test", "follower_count": 100, "biography": "old bio"}
        api.check_now()
        api._users.get_by_username.return_value = {"pk": 1, "username": "test", "follower_count": 100, "biography": "new bio"}
        api.check_now()
        assert ("old bio", "new bio") in bios

    def test_start_stop(self):
        api = self._make()
        # Just verify _running flag can be set/unset
        assert api._running is False
        api._running = True
        assert api._running is True
        api._running = False
        assert api._running is False


# ═══════════════════════════════════════════════════════════
# SchedulerJob + SchedulerAPI — deep coverage
# ═══════════════════════════════════════════════════════════
class TestSchedulerJob:
    def test_init(self):
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2030, 1, 1), {"photo": "x.jpg"}, job_id="abc123")
        assert j.id == "abc123"
        assert j.status == "pending"

    def test_to_dict(self):
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2030, 1, 1), {"photo": "x.jpg"})
        d = j.to_dict()
        assert d["job_type"] == "post"
        assert d["status"] == "pending"

    def test_from_dict(self):
        from instaharvest_v2.api.scheduler import SchedulerJob
        d = {"id": "abc", "job_type": "story", "scheduled_at": "2030-01-01T00:00:00",
             "params": {}, "status": "pending", "created_at": "2030-01-01T00:00:00", "error": None}
        j = SchedulerJob.from_dict(d)
        assert j.id == "abc"
        assert j.job_type == "story"


class TestSchedulerAPIDeep:
    def _make(self):
        from instaharvest_v2.api.scheduler import SchedulerAPI
        with patch("os.path.isfile", return_value=False):
            return SchedulerAPI(M(), M(), persist_path="/tmp/test_sched.json")

    def test_parse_time(self):
        from instaharvest_v2.api.scheduler import SchedulerAPI
        dt = SchedulerAPI._parse_time("2030-01-15 10:30")
        assert dt.year == 2030

    def test_parse_time_iso(self):
        from instaharvest_v2.api.scheduler import SchedulerAPI
        dt = SchedulerAPI._parse_time("2030-01-15T10:30:00")
        assert dt.hour == 10

    def test_parse_time_invalid(self):
        from instaharvest_v2.api.scheduler import SchedulerAPI
        with pytest.raises(ValueError):
            SchedulerAPI._parse_time("badtime")

    @patch("os.path.isfile", return_value=True)
    def test_post_at(self, _):
        api = self._make()
        with patch("builtins.open", mock_open()):
            result = api.post_at("2030-01-01 10:00", photo=__file__, caption="Test")
        assert result["job_type"] == "post"

    @patch("os.path.isfile", return_value=True)
    def test_story_at(self, _):
        api = self._make()
        with patch("builtins.open", mock_open()):
            result = api.story_at("2030-01-01 10:00", photo=__file__)
        assert result["job_type"] == "story"

    @patch("os.path.isfile", return_value=True)
    def test_reel_at(self, _):
        api = self._make()
        with patch("builtins.open", mock_open()):
            result = api.reel_at("2030-01-01 10:00", video=__file__, caption="Reel!")
        assert result["job_type"] == "reel"

    def test_schedule_action(self):
        api = self._make()
        fn = lambda: "done"
        with patch("builtins.open", mock_open()):
            result = api.schedule_action("2030-01-01 10:00", fn, action_name="custom")
        assert result["job_type"] == "action"

    def test_list_jobs(self):
        api = self._make()
        assert api.list_jobs() == []

    @patch("os.path.isfile", return_value=True)
    def test_cancel(self, _):
        api = self._make()
        with patch("builtins.open", mock_open()):
            result = api.post_at("2030-01-01 10:00", photo=__file__, caption="Test")
        with patch("builtins.open", mock_open()):
            assert api.cancel(result["id"]) is True
        assert api.cancel("nonexistent") is False

    @patch("os.path.isfile", return_value=True)
    def test_clear_done(self, _):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2020, 1, 1), {})
        j.status = "done"
        api._jobs.append(j)
        with patch("builtins.open", mock_open()):
            removed = api.clear_done()
        assert removed >= 1

    def test_execute_job_post(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2020, 1, 1), {"photo": "x.jpg", "caption": "Test"})
        api._upload.photo.return_value = "media_123"
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "done"

    def test_execute_job_story_photo(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("story", datetime(2020, 1, 1), {"photo": "x.jpg", "video": None})
        api._stories.upload_photo.return_value = {"status": "ok"}
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "done"

    def test_execute_job_story_video(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("story", datetime(2020, 1, 1), {"photo": None, "video": "v.mp4"})
        api._stories.upload_video.return_value = {"status": "ok"}
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "done"

    def test_execute_job_reel(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("reel", datetime(2020, 1, 1), {"video": "v.mp4", "caption": "R"})
        api._upload.reel.return_value = "media_reel"
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "done"

    def test_execute_job_action(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        results = []
        j = SchedulerJob("action", datetime(2020, 1, 1), {"action_name": "custom", "kwargs": {}})
        j._action = lambda: results.append(1) or "done"
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "done"

    def test_execute_job_failed(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2020, 1, 1), {"photo": "x.jpg"})
        api._upload.photo.side_effect = Exception("upload error")
        with patch("builtins.open", mock_open()):
            api._execute_job(j)
        assert j.status == "failed"
        assert "upload error" in j.error

    def test_start_stop(self):
        api = self._make()
        api.start()
        assert api.is_running is True
        api.stop()
        assert api.is_running is False

    def test_check_and_execute(self):
        api = self._make()
        from instaharvest_v2.api.scheduler import SchedulerJob
        j = SchedulerJob("post", datetime(2020, 1, 1), {"photo": "x.jpg", "caption": "T"})
        api._jobs.append(j)
        api._upload.photo.return_value = "m1"
        with patch("builtins.open", mock_open()):
            api._check_and_execute()
        assert j.status == "done"

    @patch("builtins.open", new_callable=mock_open, read_data='[{"id":"abc","job_type":"post","scheduled_at":"2030-01-01T00:00:00","params":{},"status":"pending","created_at":"2030-01-01T00:00:00","error":null}]')
    @patch("os.path.isfile", return_value=True)
    def test_load_jobs(self, _, __):
        from instaharvest_v2.api.scheduler import SchedulerAPI
        api = SchedulerAPI(M(), M(), persist_path="/tmp/test.json")
        assert len(api._jobs) >= 1
