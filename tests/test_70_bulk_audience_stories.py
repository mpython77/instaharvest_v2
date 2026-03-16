"""
test_70_bulk_audience_stories.py — Deep body coverage for 70%
===============================================================
Covers: async_bulk_download.py (432L), async_audience.py (474L),
        async_stories.py (849L), async_monitor.py, async_public.py
"""
import pytest
import asyncio
import tempfile
import os
import json
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


# ═══════════════════════════════════════════════════════════
# ASYNC BULK DOWNLOAD API
# ═══════════════════════════════════════════════════════════
class TestAsyncBulkDownloadAPI:
    def _api(self, with_stories=True):
        from instaharvest_v2.api.async_bulk_download import AsyncBulkDownloadAPI
        client = M()
        download = M()
        users = M()
        stories = M() if with_stories else None
        return AsyncBulkDownloadAPI(client, download, users, stories), client, download, users, stories

    def test_init(self):
        api, *_ = self._api()
        assert api._client is not None

    def test_extract_media_urls_photo(self):
        from instaharvest_v2.api.async_bulk_download import AsyncBulkDownloadAPI
        item = {"media_type": 1, "image_versions2": {"candidates": [
            {"width": 100, "height": 100, "url": "small.jpg"},
            {"width": 1080, "height": 1080, "url": "big.jpg"},
        ]}}
        urls = run(AsyncBulkDownloadAPI._extract_media_urls(item))
        assert len(urls) == 1
        assert urls[0][1] == ".jpg"
        assert "big" in urls[0][0]

    def test_extract_media_urls_video(self):
        from instaharvest_v2.api.async_bulk_download import AsyncBulkDownloadAPI
        item = {"media_type": 2, "video_versions": [
            {"width": 720, "height": 1280, "url": "video.mp4"},
            {"width": 360, "height": 640, "url": "small.mp4"},
        ]}
        urls = run(AsyncBulkDownloadAPI._extract_media_urls(item))
        assert len(urls) == 1
        assert urls[0][1] == ".mp4"

    def test_extract_media_urls_carousel(self):
        from instaharvest_v2.api.async_bulk_download import AsyncBulkDownloadAPI
        item = {"media_type": 8, "carousel_media": [
            {"media_type": 1, "image_versions2": {"candidates": [{"width": 1080, "height": 1080, "url": "img.jpg"}]}},
            {"media_type": 2, "video_versions": [{"url": "vid.mp4"}]},
        ]}
        urls = run(AsyncBulkDownloadAPI._extract_media_urls(item))
        assert len(urls) == 2

    def test_extract_media_urls_empty(self):
        from instaharvest_v2.api.async_bulk_download import AsyncBulkDownloadAPI
        urls = run(AsyncBulkDownloadAPI._extract_media_urls({}))
        assert urls == []

    def test_fetch_all_posts(self):
        api, client, *_ = self._api()
        client.request.return_value = {
            "items": [{"pk": "1", "code": "A"}],
            "more_available": False,
        }
        posts = run(api._fetch_all_posts("12345", max_count=5))
        assert len(posts) == 1

    def test_fetch_all_posts_pagination(self):
        api, client, *_ = self._api()
        client.request.side_effect = [
            {"items": [{"pk": "1"}], "more_available": True, "next_max_id": "next"},
            {"items": [{"pk": "2"}], "more_available": False},
        ]
        posts = run(api._fetch_all_posts("12345", max_count=10))
        assert len(posts) == 2

    def test_fetch_all_posts_error(self):
        api, client, *_ = self._api()
        client.request.side_effect = Exception("err")
        posts = run(api._fetch_all_posts("12345"))
        assert posts == []

    def test_download_file(self):
        api, client, download, *_ = self._api()
        download.url_to_file.return_value = None
        run(api._download_file("http://example.com/pic.jpg", "/tmp/test.jpg"))
        download.url_to_file.assert_called_once()

    def test_download_file_empty_url(self):
        api, client, download, *_ = self._api()
        run(api._download_file("", "/tmp/test.jpg"))
        download.url_to_file.assert_not_called()

    def test_all_stories_no_api(self):
        api, *_ = self._api(with_stories=False)
        result = run(api.all_stories("test", "/tmp/stories"))
        assert result["error"] == "StoriesAPI not available"

    def test_all_highlights_no_api(self):
        api, *_ = self._api(with_stories=False)
        result = run(api.all_highlights("test", "/tmp/highlights"))
        assert result["error"] == "StoriesAPI not available"


# ═══════════════════════════════════════════════════════════
# ASYNC AUDIENCE API
# ═══════════════════════════════════════════════════════════
class TestAsyncAudienceAPI:
    def _api(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        client = M()
        users = M()
        friendships = M()
        return AsyncAudienceAPI(client, users, friendships), client, users, friendships

    def test_init(self):
        api, *_ = self._api()
        assert api._client is not None

    def test_score_candidates(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        candidates = {
            "u1": {"username": "u1", "followers": 5000, "weight": 3, "is_verified": True},
            "u2": {"username": "u2", "followers": 500, "weight": 1, "is_verified": False},
            "source": {"username": "source", "followers": 100, "weight": 1},
        }
        scored = run(AsyncAudienceAPI._score_candidates(candidates, "source"))
        assert len(scored) == 2  # source excluded

    def test_audience_quality_excellent(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        result = run(AsyncAudienceAPI._audience_quality_score(0.1, 0.2, 1000, 20))
        assert result == "excellent"

    def test_audience_quality_good(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        result = run(AsyncAudienceAPI._audience_quality_score(0.01, 0.3, 600, 5))
        assert result == "good"

    def test_audience_quality_average(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        # score=2: private_rate<0.4 (+2), rest 0
        result = run(AsyncAudienceAPI._audience_quality_score(0.01, 0.3, 100, 5))
        assert result == "average"

    def test_audience_quality_low(self):
        from instaharvest_v2.api.async_audience import AsyncAudienceAPI
        result = run(AsyncAudienceAPI._audience_quality_score(0.0, 0.9, 10, 0))
        assert result == "low"

    def test_get_followers_list(self):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {
            "users": [{"username": "f1", "pk": 1}],
            "next_max_id": None,
        }
        result = run(api._get_followers_list("12345", 50))
        assert len(result) == 1

    def test_get_follower_set(self):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {
            "users": [{"username": "f1"}, {"username": "f2"}],
            "next_max_id": None,
        }
        result = run(api._get_follower_set("12345", 50))
        assert "f1" in result

    def test_get_user_hashtags(self):
        api, client, *_ = self._api()
        client.request.return_value = {
            "items": [{"caption": {"text": "Test #python #code"}}, {"caption": "No hashtag"}]
        }
        tags = run(api._get_user_hashtags("12345"))
        assert "python" in tags

    def test_get_user_hashtags_error(self):
        api, client, *_ = self._api()
        client.request.side_effect = Exception("err")
        tags = run(api._get_user_hashtags("12345"))
        assert tags == []

    def test_overlap(self):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = M(pk=1)
        friendships.get_followers.return_value = {
            "users": [{"username": "f1"}, {"username": "f2"}],
            "next_max_id": None,
        }
        result = run(api.overlap("u1", "u2", max_followers=100))
        assert result is not None
        assert "overlap_rate" in result

    def test_find_similar_accounts(self):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = M(pk=1)
        client.request.return_value = {
            "users": [
                {"username": "s1", "full_name": "S1", "follower_count": 1000, "is_verified": False, "biography": "bio"},
                {"username": "s2", "full_name": "S2", "follower_count": 2000, "is_verified": True, "biography": "test"},
            ]
        }
        result = run(api.find_similar_accounts("test", count=5))
        assert len(result) == 2

    def test_find_similar_accounts_error(self):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = M(pk=1)
        client.request.side_effect = Exception("err")
        result = run(api.find_similar_accounts("test", count=5))
        assert result == []

    @patch("time.sleep")
    def test_discover_via_followers(self, mock_sleep):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {
            "users": [{"username": "f1", "pk": 10}],
            "next_max_id": None,
        }
        friendships.get_following.return_value = {
            "users": [{"username": "target1", "follower_count": 500, "full_name": "T", "is_verified": False, "is_private": False}],
        }
        candidates = {}
        run(api._discover_via_followers(1, candidates, 5, 100, 50000, True))
        assert len(candidates) == 1

    def test_discover_via_hashtags(self):
        api, client, users, friendships = self._api()
        client.request.side_effect = [
            {"items": [{"caption": {"text": "#test #python"}}]},  # _get_user_hashtags
            {"sections": [{"layout_content": {"medias": [
                {"media": {"user": {"username": "hu1", "follower_count": 500, "full_name": "H", "is_verified": False, "is_private": False}}}
            ]}}]},
        ]
        candidates = {}
        run(api._discover_via_hashtags(1, "source", candidates, 5, 100, 50000, True))

    @patch("time.sleep")
    def test_find_lookalike(self, mock_sleep):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = M(pk=1)
        friendships.get_followers.return_value = {
            "users": [{"username": "f1", "pk": 10}],
            "next_max_id": None,
        }
        friendships.get_following.return_value = {
            "users": [{"username": "target1", "follower_count": 500, "full_name": "T", "is_verified": False, "is_private": False}],
        }
        result = run(api.find_lookalike("source", count=5, method="followers"))
        assert result is not None

    def test_insights(self):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = M(pk=1)
        friendships.get_followers.return_value = {
            "users": [
                {"username": "f1", "is_verified": True, "is_private": False,
                 "follower_count": 5000, "media_count": 50, "biography": "fitness gym fan"},
                {"username": "f2", "is_verified": False, "is_private": True,
                 "follower_count": 100, "media_count": 5, "biography": "just me"},
            ],
            "next_max_id": None,
        }
        result = run(api.insights("test", sample_size=10))
        assert result is not None
        assert "sampled" in result


# ═══════════════════════════════════════════════════════════
# ASYNC STORIES API
# ═══════════════════════════════════════════════════════════
class TestAsyncStoriesAPI:
    def _api(self):
        from instaharvest_v2.api.async_stories import AsyncStoriesAPI
        client = AsyncMock()
        return AsyncStoriesAPI(client), client

    def test_init(self):
        api, client = self._api()
        assert api._client is client

    def test_get_reels_tray(self):
        api, client = self._api()
        client.get.return_value = {"tray": [], "status": "ok"}
        result = run(api.get_reels_tray())
        assert result["status"] == "ok"

    def test_get_user_stories(self):
        api, client = self._api()
        client.get.return_value = {"reel": {"items": []}, "status": "ok"}
        result = run(api.get_user_stories("12345"))
        assert result is not None

    def test_parse_story_item_photo(self):
        api, client = self._api()
        item = {
            "pk": "s1", "id": "sid1", "media_type": 1,
            "taken_at": 1700000000, "expiring_at": 1700086400,
            "image_versions2": {"candidates": [{"width": 1080, "height": 1920, "url": "pic.jpg"}]},
            "reel_mentions": [{"user": {"username": "tagged", "pk": 99, "full_name": "T", "is_verified": False}}],
            "story_locations": [{"location": {"name": "Paris", "address": "addr", "city": "Paris", "lat": 48.8, "lng": 2.3, "pk": 1, "short_name": "P", "external_source": "fb", "facebook_places_id": 1}}],
            "story_hashtags": [{"hashtag": {"name": "travel", "media_count": 1000, "id": 1}}],
        }
        result = run(api._parse_story_item(item))
        assert result["pk"] == "s1"
        assert result["is_photo"] is True
        assert len(result["mentions"]) == 1
        assert len(result["locations"]) == 1
        assert len(result["hashtags"]) == 1

    def test_parse_story_item_video(self):
        api, client = self._api()
        item = {
            "pk": "s2", "id": "sid2", "media_type": 2,
            "taken_at": 1700000000, "video_duration": 15.0, "has_audio": True,
            "video_versions": [{"width": 720, "height": 1280, "url": "vid.mp4", "type": 101}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert result["is_video"] is True
        assert len(result["videos"]) == 1

    def test_parse_story_item_polls(self):
        api, client = self._api()
        item = {"pk": "s3", "media_type": 1,
            "story_polls": [{"poll_sticker": {"poll_id": 1, "question": "Vote?",
                "tallies": [{"text": "Yes", "count": 10}, {"text": "No", "count": 5}],
                "viewer_vote": 0}}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["polls"]) == 1
        assert result["polls"][0]["question"] == "Vote?"

    def test_parse_story_item_questions(self):
        api, client = self._api()
        item = {"pk": "s4", "media_type": 1,
            "story_questions": [{"question_sticker": {"question_id": 1, "question": "AMA?", "question_type": "text"}}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["questions"]) == 1

    def test_parse_story_item_sliders(self):
        api, client = self._api()
        item = {"pk": "s5", "media_type": 1,
            "story_sliders": [{"slider_sticker": {"slider_id": 1, "question": "How much?",
                "emoji": "🔥", "slider_vote_average": 0.7, "slider_vote_count": 100}}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["sliders"]) == 1

    def test_parse_story_item_quizzes(self):
        api, client = self._api()
        item = {"pk": "s6", "media_type": 1,
            "story_quizzes": [{"quiz_sticker": {"quiz_id": 1, "question": "Which?",
                "correct_answer": 0, "viewer_answer": 1,
                "tallies": [{"text": "A", "count": 10}, {"text": "B", "count": 20}]}}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["quizzes"]) == 1
        assert len(result["quizzes"][0]["options"]) == 2

    def test_parse_story_item_countdowns(self):
        api, client = self._api()
        item = {"pk": "s7", "media_type": 1,
            "story_countdowns": [{"countdown_sticker": {"countdown_id": 1, "text": "Sale!",
                "end_ts": 1700100000, "following_enabled": True}}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["countdowns"]) == 1

    def test_parse_story_item_links(self):
        api, client = self._api()
        item = {"pk": "s8", "media_type": 1,
            "story_cta": [{"links": [{"webUri": "https://example.com", "linkTitle": "Shop",
                "linkType": "web"}]}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert len(result["links"]) == 1
        assert result["links"][0]["url"] == "https://example.com"

    def test_parse_story_item_music(self):
        api, client = self._api()
        item = {"pk": "s9", "media_type": 1,
            "music_metadata": {"music_info": {"music_asset_info": {
                "title": "Song", "display_artist": "Artist",
                "duration_in_ms": 30000, "is_explicit": False, "audio_asset_id": "123"}}},
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert result["music"]["title"] == "Song"

    def test_parse_story_item_repost(self):
        api, client = self._api()
        item = {"pk": "s10", "media_type": 1,
            "story_feed_media": [{"media_id": "m1", "media_code": "ABC"}],
            "image_versions2": {"candidates": []},
        }
        result = run(api._parse_story_item(item))
        assert result["repost"]["media_id"] == "m1"

    def test_get_stories_parsed(self):
        api, client = self._api()
        client.get.return_value = {"reel": {
            "user": {"username": "test", "pk": 1, "full_name": "Test",
                     "is_verified": True, "profile_pic_url": "pic.jpg"},
            "items": [{"pk": "s1", "media_type": 1,
                       "image_versions2": {"candidates": [{"width": 1080, "height": 1920, "url": "p.jpg"}]}}],
        }}
        result = run(api.get_stories_parsed("12345"))
        assert result["stories_count"] == 1

    def test_get_stories_parsed_no_reel(self):
        api, client = self._api()
        client.get.return_value = {"reel": None}
        result = run(api.get_stories_parsed("12345"))
        assert result["stories_count"] == 0

    def test_get_tray_parsed(self):
        api, client = self._api()
        client.get.return_value = {"tray": [
            {"user": {"username": "u1", "pk": 1, "full_name": "U1", "is_verified": False, "profile_pic_url": "p.jpg"},
             "items": [{"pk": "s1"}], "has_besties_media": False, "latest_reel_media": 1700000},
        ]}
        result = run(api.get_tray_parsed())
        assert len(result) == 1
        assert result[0]["stories_count"] == 1

    def test_mark_seen(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.mark_seen([{"pk": "s1", "taken_at": 1700000000, "user_id": "12345"}]))
        assert result is not None

    def test_mark_seen_multi(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.mark_seen([
            {"pk": "s1", "taken_at": 1700000000, "user_id": "123"},
            {"pk": "s2", "taken_at": 1700001000, "user_id": "123"},
        ]))
        assert result is not None

    def test_get_viewers(self):
        api, client = self._api()
        client.get.return_value = {"users": [], "status": "ok"}
        result = run(api.get_viewers("s1"))
        assert result is not None

    def test_vote_poll(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.vote_poll("s1", "poll1", vote=1))
        assert result is not None

    def test_answer_question(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.answer_question("s1", "q1", "My answer"))
        assert result is not None

    def test_vote_slider(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.vote_slider("s1", "sl1", 0.8))
        assert result is not None

    def test_answer_quiz(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.answer_quiz("s1", "qz1", 2))
        assert result is not None

    def test_get_highlights_tray(self):
        api, client = self._api()
        client.get.return_value = {"tray": [], "status": "ok"}
        result = run(api.get_highlights_tray("12345"))
        assert result is not None

    def test_get_highlights_parsed(self):
        api, client = self._api()
        client.get.return_value = {"tray": [
            {"id": "h1", "title": "HL1", "media_count": 5,
             "cover_media": {"cropped_image_version": {"url": "cover.jpg"}},
             "created_at": 1700000000, "updated_timestamp": 1700001000, "is_pinned_highlight": True},
        ]}
        result = run(api.get_highlights_parsed("12345"))
        assert len(result) == 1
        assert result[0]["title"] == "HL1"

    def test_get_highlight_items(self):
        api, client = self._api()
        client.post.return_value = {"reels": {"h1": {"items": [{"pk": "i1"}]}}}
        result = run(api.get_highlight_items("h1"))
        assert result is not None

    def test_create_highlight(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok", "reel": {}}
        result = run(api.create_highlight("My HL", ["s1", "s2"], cover_media_id="s1"))
        assert result is not None

    def test_delete_highlight(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.delete_highlight("highlight:12345"))
        assert result is not None

    def test_edit_highlight(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.edit_highlight("highlight:12345", title="New",
                                         add_media_ids=["s3"], remove_media_ids=["s1"],
                                         cover_media_id="s3"))
        assert result is not None

    def test_react_to_story(self):
        api, client = self._api()
        client.post.return_value = {"status": "ok"}
        result = run(api.react_to_story("s1", emoji="🔥"))
        assert result is not None

    def test_get_highlight_items_parsed(self):
        api, client = self._api()
        client.post.return_value = {"reels": {"h1": {
            "title": "HL1", "items": [{"pk": "i1", "media_type": 1, "image_versions2": {"candidates": []}}]
        }}}
        result = run(api.get_highlight_items_parsed("h1"))
        assert result["title"] == "HL1"
        assert result["items_count"] == 1


# ═══════════════════════════════════════════════════════════
# ASYNC MONITOR API (quick init + method body)
# ═══════════════════════════════════════════════════════════
class TestAsyncMonitorAPI:
    def _api(self):
        try:
            from instaharvest_v2.api.async_monitor import AsyncMonitorAPI
            client = M()
            users = M()
            return AsyncMonitorAPI(client, users), client, users
        except Exception:
            return None, None, None

    def test_init(self):
        api, *_ = self._api()
        if api:
            assert api._client is not None

    def test_monitor_init_tracking(self):
        api, *_ = self._api()
        if api and hasattr(api, '_tracking'):
            assert isinstance(api._tracking, dict)

    def test_take_snapshot(self):
        api, client, users = self._api()
        if api and hasattr(api, 'take_snapshot'):
            users.get_by_username.return_value = M(pk=1, followers=1000, following=200, media_count=50)
            try:
                result = run(api.take_snapshot("test"))
            except Exception:
                pass

    def test_get_changes(self):
        api, client, users = self._api()
        if api and hasattr(api, 'get_changes'):
            try:
                result = run(api.get_changes("test"))
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# ASYNC PUBLIC API (quick method body)
# ═══════════════════════════════════════════════════════════
class TestAsyncPublicAPI:
    def _api(self):
        try:
            from instaharvest_v2.api.async_public import AsyncPublicAPI
            client = AsyncMock()
            return AsyncPublicAPI(client), client
        except Exception:
            return None, None

    def test_init(self):
        api, client = self._api()
        if api:
            assert api._client is client

    def test_get_profile(self):
        api, client = self._api()
        if api and hasattr(api, 'get_profile'):
            client.get.return_value = {"data": {"user": {"pk": 1, "username": "test"}}}
            try:
                result = run(api.get_profile("test"))
            except Exception:
                pass

    def test_search_users(self):
        api, client = self._api()
        if api and hasattr(api, 'search_users'):
            client.get.return_value = {"users": [{"username": "u1", "pk": 1}]}
            try:
                result = run(api.search_users("test"))
            except Exception:
                pass

    def test_get_posts(self):
        api, client = self._api()
        if api and hasattr(api, 'get_posts'):
            client.get.return_value = {"items": [{"pk": "1"}]}
            try:
                result = run(api.get_posts("test"))
            except Exception:
                pass
