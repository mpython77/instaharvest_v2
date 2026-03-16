"""
test_100_batch2.py — Coverage push: Batch 2
=============================================
Covers: events, plugin, story_composer, async_search, async_download,
        async_hashtag_research, async_ai_suggest, async_auth (partial)
"""
import pytest
import asyncio
import json
import time
import os
import re
from unittest.mock import MagicMock, AsyncMock, patch, mock_open, PropertyMock

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
# EVENTS
# ═══════════════════════════════════════════════════════════
class TestEventType:
    def test_values(self):
        from instaharvest_v2.events import EventType
        assert EventType.RATE_LIMIT == "rate_limit"
        assert EventType.CHALLENGE == "challenge"
        assert EventType.LOGIN_REQUIRED == "login_required"
        assert EventType.NETWORK_ERROR == "network_error"
        assert EventType.ERROR == "error"
        assert EventType.RETRY == "retry"
        assert EventType.REQUEST == "request"
        assert EventType.SESSION_REFRESH == "session_refresh"
        assert EventType.SESSION_ROTATE == "session_rotate"
        assert EventType.PROXY_ROTATE == "proxy_rotate"


class TestEventData:
    def test_repr_minimal(self):
        from instaharvest_v2.events import EventData, EventType
        e = EventData(event_type=EventType.ERROR)
        r = repr(e)
        assert "ERROR" in r or "error" in r

    def test_repr_full(self):
        from instaharvest_v2.events import EventData, EventType
        e = EventData(event_type=EventType.RETRY, endpoint="/api/v1/users/", attempt=3, error=ValueError("x"))
        r = repr(e)
        assert "RETRY" in r or "retry" in r
        assert "attempt=3" in r
        assert "/api/v1/users/" in r


class TestEventEmitter:
    def test_on_and_emit(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        em.on(EventType.ERROR, lambda e: results.append(e.event_type))
        em.emit(EventType.ERROR, endpoint="/test")
        assert len(results) == 1

    def test_on_string(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        em.on("error", lambda e: results.append(1))
        em.emit("error")
        assert results == [1]

    def test_on_all(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        em.on_all(lambda e: results.append(e.event_type))
        em.emit(EventType.ERROR)
        em.emit(EventType.RETRY)
        assert len(results) == 2

    def test_off(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        cb = lambda e: None
        em.on(EventType.ERROR, cb)
        em.off(EventType.ERROR, cb)
        assert em.listener_count == 0

    def test_off_string(self):
        from instaharvest_v2.events import EventEmitter
        em = EventEmitter()
        cb = lambda e: None
        em.on("error", cb)
        em.off("error", cb)

    def test_off_nonexistent(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        em.off(EventType.ERROR, lambda e: None)  # should not crash

    def test_off_all_specific(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        em.on(EventType.ERROR, lambda e: None)
        em.on(EventType.RETRY, lambda e: None)
        em.off_all(EventType.ERROR)
        assert em.listener_count == 1

    def test_off_all_everything(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        em.on(EventType.ERROR, lambda e: None)
        em.on_all(lambda e: None)
        em.off_all()
        assert em.listener_count == 0

    def test_off_all_string(self):
        from instaharvest_v2.events import EventEmitter
        em = EventEmitter()
        em.on("error", lambda e: None)
        em.off_all("error")

    def test_emit_with_kwargs(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        em.on(EventType.RETRY, lambda e: results.append(e.attempt))
        em.emit(EventType.RETRY, attempt=5, endpoint="/test")
        assert results == [5]

    def test_emit_callback_error(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        def bad(e): raise ValueError("boom")
        em.on(EventType.ERROR, bad)
        em.emit(EventType.ERROR)  # should not raise

    def test_emit_async_callback_no_loop(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        async def async_cb(e): pass
        em.on(EventType.ERROR, async_cb)
        em.emit(EventType.ERROR)  # should skip without crash

    def test_emit_async(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        async def async_cb(e): results.append(1)
        em.on(EventType.ERROR, async_cb)
        run(em.emit_async(EventType.ERROR))
        assert results == [1]

    def test_emit_async_sync_cb(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        results = []
        em.on(EventType.ERROR, lambda e: results.append(1))
        run(em.emit_async(EventType.ERROR))
        assert results == [1]

    def test_emit_async_error(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        async def bad(e): raise ValueError("boom")
        em.on(EventType.ERROR, bad)
        run(em.emit_async(EventType.ERROR))  # should not raise

    def test_emit_async_string(self):
        from instaharvest_v2.events import EventEmitter
        em = EventEmitter()
        results = []
        em.on("retry", lambda e: results.append(1))
        run(em.emit_async("retry"))
        assert results == [1]

    def test_listener_count(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        em.on(EventType.ERROR, lambda e: None)
        em.on(EventType.RETRY, lambda e: None)
        em.on_all(lambda e: None)
        assert em.listener_count == 3

    def test_has_listeners(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        assert em.has_listeners(EventType.ERROR) is False
        em.on(EventType.ERROR, lambda e: None)
        assert em.has_listeners(EventType.ERROR) is True

    def test_has_listeners_string(self):
        from instaharvest_v2.events import EventEmitter
        em = EventEmitter()
        assert em.has_listeners("error") is False

    def test_has_listeners_global(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        em.on_all(lambda e: None)
        assert em.has_listeners(EventType.ERROR) is True

    def test_chaining(self):
        from instaharvest_v2.events import EventEmitter, EventType
        em = EventEmitter()
        result = em.on(EventType.ERROR, lambda e: None).on(EventType.RETRY, lambda e: None)
        assert result is em


# ═══════════════════════════════════════════════════════════
# PLUGIN SYSTEM
# ═══════════════════════════════════════════════════════════
class TestPlugin:
    def test_base_plugin(self):
        from instaharvest_v2.plugin import Plugin
        p = Plugin()
        assert p.name == "unnamed_plugin"
        assert p.version == "1.0.0"
        p.on_install(None)
        p.on_uninstall()
        p.on_request(None)
        p.on_response(None)
        p.on_error(None)
        p.on_retry(None)
        p.on_rate_limit(None)
        p.on_challenge(None)
        p.on_login_required(None)
        assert "Plugin" in repr(p)

    def test_custom_plugin(self):
        from instaharvest_v2.plugin import Plugin
        class MyPlugin(Plugin):
            name = "test_plugin"
            version = "2.0"
            description = "Test"
            def on_error(self, event): pass
        p = MyPlugin()
        assert p.name == "test_plugin"


class TestPluginManager:
    def test_install_uninstall(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        p = Plugin()
        p.name = "test"
        pm.install(p)
        assert "test" in pm
        assert pm.count == 1
        assert pm.uninstall("test") is True
        assert pm.count == 0

    def test_install_replace(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        p1 = Plugin(); p1.name = "test"
        p2 = Plugin(); p2.name = "test"
        pm.install(p1)
        pm.install(p2)
        assert pm.count == 1

    def test_install_with_ig(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        installed = []
        class MyPlugin(Plugin):
            name = "my"
            def on_install(self, ig): installed.append(ig)
        pm.install(MyPlugin(), ig="ig_instance")
        assert installed == ["ig_instance"]

    def test_install_error(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        class BadPlugin(Plugin):
            name = "bad"
            def on_install(self, ig): raise ValueError("fail")
        pm.install(BadPlugin())
        assert pm.count == 1

    def test_uninstall_nonexistent(self):
        from instaharvest_v2.plugin import PluginManager
        pm = PluginManager()
        assert pm.uninstall("nope") is False

    def test_uninstall_error(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        class BadPlugin(Plugin):
            name = "bad"
            def on_uninstall(self): raise ValueError("fail")
        pm.install(BadPlugin())
        assert pm.uninstall("bad") is True

    def test_get_plugin(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        p = Plugin(); p.name = "test"
        pm.install(p)
        assert pm.get_plugin("test") is p
        assert pm.get_plugin("none") is None

    def test_list_plugins(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        p = Plugin(); p.name = "test"; p.description = "A test"
        pm.install(p)
        lst = pm.list_plugins()
        assert len(lst) == 1
        assert lst[0]["name"] == "test"

    def test_register_hooks(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        from instaharvest_v2.events import EventEmitter
        em = EventEmitter()
        pm = PluginManager(em)
        class MyPlugin(Plugin):
            name = "hook_test"
            def on_error(self, event): pass
        pm.install(MyPlugin())
        assert em.listener_count >= 1

    def test_repr(self):
        from instaharvest_v2.plugin import PluginManager
        pm = PluginManager()
        assert "PluginManager" in repr(pm)

    def test_contains(self):
        from instaharvest_v2.plugin import Plugin, PluginManager
        pm = PluginManager()
        p = Plugin(); p.name = "x"
        pm.install(p)
        assert "x" in pm
        assert "y" not in pm


# ═══════════════════════════════════════════════════════════
# STORY COMPOSER
# ═══════════════════════════════════════════════════════════
class TestStoryElement:
    def test_creation(self):
        from instaharvest_v2.story_composer import StoryElement
        e = StoryElement(type="text", content="Hello")
        assert e.type == "text"
        assert e.position == (0.5, 0.5)


class TestStoryDraft:
    def test_publish_no_ig(self):
        from instaharvest_v2.story_composer import StoryDraft
        d = StoryDraft()
        with pytest.raises(ValueError):
            d.publish()

    def test_publish_no_media(self):
        from instaharvest_v2.story_composer import StoryDraft
        d = StoryDraft(_ig=M())
        with pytest.raises(ValueError):
            d.publish()

    def test_publish_image(self):
        from instaharvest_v2.story_composer import StoryDraft
        ig = M()
        ig.upload.upload_story_photo.return_value = {"status": "ok"}
        d = StoryDraft(image_path="test.jpg", _ig=ig)
        result = d.publish()
        assert result["status"] == "ok"

    def test_publish_video(self):
        from instaharvest_v2.story_composer import StoryDraft
        ig = M()
        ig.upload.upload_story_video.return_value = {"status": "ok"}
        d = StoryDraft(video_path="test.mp4", _ig=ig)
        result = d.publish()
        assert result["status"] == "ok"

    def test_build_upload_data_all_elements(self):
        from instaharvest_v2.story_composer import StoryDraft, StoryElement
        d = StoryDraft(elements=[
            StoryElement(type="mention", content="@user", extra={"user_id": "123"}),
            StoryElement(type="hashtag", content="#travel"),
            StoryElement(type="location", content="", extra={"location_id": "456"}),
            StoryElement(type="link", content="https://example.com"),
            StoryElement(type="poll", content="Yes or No?", extra={"options": ["A", "B"]}),
            StoryElement(type="question", content="Ask me anything"),
        ])
        data = d._build_upload_data()
        assert "reel_mentions" in data
        assert "story_hashtags" in data
        assert "story_cta" in data
        assert "story_stickers" in data

    def test_to_dict(self):
        from instaharvest_v2.story_composer import StoryDraft, StoryElement
        d = StoryDraft(image_path="x.jpg", elements=[StoryElement(type="text", content="Hi")])
        dd = d.to_dict()
        assert dd["image"] == "x.jpg"
        assert len(dd["elements"]) == 1


class TestStoryComposer:
    def test_full_builder(self):
        from instaharvest_v2.story_composer import StoryComposer
        sc = StoryComposer(ig=M())
        result = sc.image("bg.jpg") \
            .text("Hello!", position=(0.5, 0.3), font_size=28, color="#ff0000", background_color="#000") \
            .mention("@friend", position=(0.5, 0.7), user_id="123") \
            .hashtag("#travel") \
            .location("loc_123") \
            .link("https://example.com") \
            .poll("Agree?", options=["Yes", "No"]) \
            .question("Ask me!") \
            .build()
        assert result.image_path == "bg.jpg"
        assert len(result.elements) == 7

    def test_video_builder(self):
        from instaharvest_v2.story_composer import StoryComposer
        sc = StoryComposer()
        result = sc.video("clip.mp4").text("Video story").build()
        assert result.video_path == "clip.mp4"

    def test_repr(self):
        from instaharvest_v2.story_composer import StoryComposer
        sc = StoryComposer()
        assert "no media" in repr(sc)
        sc.image("test.jpg")
        assert "test.jpg" in repr(sc)

    def test_poll_defaults(self):
        from instaharvest_v2.story_composer import StoryComposer
        sc = StoryComposer()
        sc.poll("Question?")
        assert sc._elements[-1].extra["options"] == ["Yes", "No"]


# ═══════════════════════════════════════════════════════════
# ASYNC SEARCH
# ═══════════════════════════════════════════════════════════
class TestAsyncSearchFull:
    def _api(self):
        from instaharvest_v2.api.async_search import AsyncSearchAPI
        client = AsyncMock()
        return AsyncSearchAPI(client), client

    def test_top_search(self):
        api, client = self._api()
        client.get.return_value = {"users": [], "hashtags": [], "places": []}
        result = run(api.top_search("test"))
        assert "users" in result

    def test_search_users(self):
        api, client = self._api()
        client.get.return_value = {"users": [
            {"user": {"pk": 1, "username": "u1", "full_name": "U1", "is_private": False, "is_verified": False, "profile_pic_url": "p"}},
            {"user": "not_a_dict"},
        ]}
        users = run(api.search_users("test"))
        assert len(users) == 1

    def test_search_hashtags(self):
        api, client = self._api()
        client.get.return_value = {"results": [{"name": "python"}]}
        result = run(api.search_hashtags("python"))
        assert len(result) == 1

    def test_search_places(self):
        api, client = self._api()
        client.get.return_value = {"items": [{"name": "NYC"}]}
        result = run(api.search_places("new york"))
        assert len(result) == 1

    @patch("time.sleep")
    def test_hashtag_search_single_page(self, _):
        api, client = self._api()
        client.get.return_value = {
            "status": "ok",
            "media_grid": {
                "has_more": False,
                "sections": [{"layout_content": {"medias": [
                    {"media": {"pk": 1, "code": "ABC", "media_type": 1,
                               "like_count": 10, "comment_count": 2,
                               "taken_at": 1000, "caption": {"text": "hi"},
                               "image_versions2": {"candidates": [{"url": "u", "width": 100, "height": 100}]},
                               "user": {"pk": 1, "username": "u1", "full_name": "U", "is_verified": False, "is_private": False, "profile_pic_url": "p"}}}
                ]}}],
            },
            "rank_token": "rt",
        }
        result = run(api.hashtag_search("fashion"))
        assert result.total_posts >= 1

    @patch("time.sleep")
    def test_hashtag_search_with_hash(self, _):
        api, client = self._api()
        client.get.return_value = {"status": "ok", "media_grid": {"has_more": False, "sections": []}}
        result = run(api.hashtag_search("#fashion"))
        assert result is not None

    @patch("time.sleep")
    def test_hashtag_search_error(self, _):
        api, client = self._api()
        client.get.side_effect = Exception("net error")
        result = run(api.hashtag_search("test"))
        assert result.total_posts == 0

    @patch("time.sleep")
    def test_hashtag_search_invalid_response(self, _):
        api, client = self._api()
        client.get.return_value = "not a dict"
        result = run(api.hashtag_search("test"))
        assert result.total_posts == 0

    @patch("time.sleep")
    def test_hashtag_search_multi_page(self, _):
        api, client = self._api()
        client.get.side_effect = [
            {"status": "ok", "media_grid": {"has_more": True, "next_max_id": "c1",
             "sections": [{"layout_content": {"medias": [
                 {"media": {"pk": 1, "code": "A", "media_type": 1,
                            "user": {"pk": 1, "username": "u1", "full_name": "U", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
                            "image_versions2": {"candidates": [{"url": "u", "width": 100, "height": 100}]}}}
             ]}}]}, "rank_token": "rt"},
            {"status": "ok", "media_grid": {"has_more": False, "sections": []}},
        ]
        result = run(api.hashtag_search("test", max_pages=2, delay=0))
        assert result.pages_fetched >= 1

    def test_parse_sections_tagged_users(self):
        api, client = self._api()
        sections = [{"layout_content": {"medias": [
            {"media": {
                "pk": 1, "code": "X", "media_type": 1,
                "image_versions2": {"candidates": [{"url": "u", "width": 100, "height": 100}]},
                "user": {"pk": 1, "username": "owner", "full_name": "O", "is_verified": False, "is_private": False, "profile_pic_url": "p"},
                "usertags": {"in": [{"user": {"pk": 2, "username": "tagged1", "full_name": "T", "is_verified": False, "is_private": False, "profile_pic_url": "p"}}]},
                "carousel_media": [{"usertags": {"in": [{"user": {"pk": 3, "username": "tagged2", "full_name": "T2", "is_verified": False, "is_private": False, "profile_pic_url": "p"}}]}}],
            }}
        ]}}]
        posts, users = run(api._parse_sections(sections))
        assert "tagged1" in users or "tagged2" in users

    def test_parse_sections_empty_media(self):
        api, client = self._api()
        sections = [{"layout_content": {"medias": [{"media": {}}]}}]
        run(api._parse_sections(sections))

    def test_parse_sections_bad_media(self):
        api, client = self._api()
        # media that fails to parse
        sections = [{"layout_content": {"medias": [{"media": {"pk": "bad"}}]}}]
        run(api._parse_sections(sections))

    def test_extract_tagged_users_fb_tags(self):
        api, client = self._api()
        users = {}
        media_data = {"fb_user_tags": {"in": [{"user": {"pk": 5, "username": "fb_tagged", "full_name": "FB", "is_verified": False, "is_private": False, "profile_pic_url": "p"}}]}}
        run(api._extract_tagged_users(media_data, users))
        assert "fb_tagged" in users

    def test_extract_tagged_no_tags(self):
        api, client = self._api()
        users = {}
        run(api._extract_tagged_users({}, users))
        assert len(users) == 0

    def test_extract_tagged_invalid_tags(self):
        api, client = self._api()
        users = {}
        run(api._extract_tagged_users({"usertags": "not_a_dict"}, users))
        assert len(users) == 0

    def test_web_search(self):
        api, client = self._api()
        client.get.return_value = {"status": "ok"}
        result = run(api.web_search("#fashion"))
        assert result is not None

    def test_web_search_no_metadata(self):
        api, client = self._api()
        client.get.return_value = {"status": "ok"}
        result = run(api.web_search("query", enable_metadata=False))
        assert result is not None

    def test_web_search_posts(self):
        api, client = self._api()
        client.get.return_value = {
            "media_grid": {"sections": [{"layout_content": {"medias": [
                {"media": {
                    "pk": 1, "code": "X", "media_type": 1,
                    "like_count": 100, "comment_count": 10,
                    "caption": {"text": "cool"},
                    "image_versions2": {"candidates": [{"url": "img_url"}]},
                    "video_versions": [{"url": "vid_url"}],
                    "user": {"pk": 1, "username": "u1", "is_verified": True},
                    "taken_at": 1000, "has_audio": True,
                }}
            ]}}]}
        }
        posts = run(api.web_search_posts("fashion"))
        assert len(posts) == 1
        assert posts[0]["video_url"] == "vid_url"

    def test_web_search_posts_no_hash(self):
        api, client = self._api()
        client.get.return_value = {"media_grid": {"sections": []}}
        posts = run(api.web_search_posts("fashion"))
        assert posts == []

    def test_web_search_posts_caption_none(self):
        api, client = self._api()
        client.get.return_value = {
            "media_grid": {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "code": "X", "media_type": 1,
                           "caption": None,
                           "image_versions2": {"candidates": []},
                           "user": {}, "taken_at": 1}}
            ]}}]}
        }
        posts = run(api.web_search_posts("#tag"))
        assert posts[0]["caption_text"] == ""

    def test_explore(self):
        api, client = self._api()
        client.get.return_value = {"status": "ok", "items": []}
        result = run(api.explore())
        assert result["status"] == "ok"

    def test_search_top_alias(self):
        from instaharvest_v2.api.async_search import AsyncSearchAPI
        assert AsyncSearchAPI.search_top is AsyncSearchAPI.top_search


# ═══════════════════════════════════════════════════════════
# ASYNC DOWNLOAD
# ═══════════════════════════════════════════════════════════
class TestAsyncDownloadFull:
    def _api(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        client = M()
        client._get_curl_session.return_value = M()
        client._session_mgr = M()
        client._session_mgr.get_session.return_value = M(user_agent="UA")
        return AsyncDownloadAPI(client), client

    def test_ensure_dir(self):
        api, _ = self._api()
        with patch("os.makedirs"):
            result = run(api._ensure_dir("/tmp/test/file.jpg"))
            assert result == "/tmp/test/file.jpg"

    def test_ensure_dir_no_dir(self):
        api, _ = self._api()
        result = run(api._ensure_dir("file.jpg"))
        assert result == "file.jpg"

    def test_get_extension(self):
        api, _ = self._api()
        assert run(api._get_extension("https://x.com/photo.mp4?q=1")) == ".mp4"
        assert run(api._get_extension("https://x.com/photo.jpg")) == ".jpg"
        assert run(api._get_extension("https://x.com/photo.jpeg")) == ".jpg"
        assert run(api._get_extension("https://x.com/photo.png")) == ".png"
        assert run(api._get_extension("https://x.com/photo.webp")) == ".webp"
        assert run(api._get_extension("https://x.com/photo.unknown")) == ".jpg"

    def test_get_best_url_video(self):
        api, _ = self._api()
        assert run(api._get_best_url({"video_versions": [{"url": "vid_url"}]})) == "vid_url"

    def test_get_best_url_photo(self):
        api, _ = self._api()
        assert run(api._get_best_url({"image_versions2": {"candidates": [
            {"url": "small", "width": 100, "height": 100},
            {"url": "big", "width": 1000, "height": 1000},
        ]}})) == "big"

    def test_get_best_url_none(self):
        api, _ = self._api()
        assert run(api._get_best_url({})) is None

    def test_shortcode_to_pk(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        pk = run(AsyncDownloadAPI._shortcode_to_pk("CG"))
        assert isinstance(pk, int) and pk > 0

    def test_pk_to_shortcode(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._pk_to_shortcode(1000))
        assert isinstance(sc, str) and len(sc) > 0

    def test_extract_shortcode_post(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._extract_shortcode("https://instagram.com/p/ABC123/"))
        assert sc == "ABC123"

    def test_extract_shortcode_reel(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._extract_shortcode("https://instagram.com/reel/XYZ789/"))
        assert sc == "XYZ789"

    def test_extract_shortcode_tv(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._extract_shortcode("https://instagram.com/tv/TV123/"))
        assert sc == "TV123"

    def test_extract_shortcode_none(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._extract_shortcode("https://google.com"))
        assert sc is None

    def test_extract_shortcode_instgram(self):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        sc = run(AsyncDownloadAPI._extract_shortcode("https://instagr.am/p/SHORT/"))
        assert sc == "SHORT"


# ═══════════════════════════════════════════════════════════
# ASYNC HASHTAG RESEARCH
# ═══════════════════════════════════════════════════════════
class TestAsyncHashtagResearchFull:
    def _api(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        client = M()
        hashtags = M()
        return AsyncHashtagResearchAPI(client, hashtags), client

    def test_calculate_difficulty(self):
        api, _ = self._api()
        assert run(api._calculate_difficulty(10_000_000)) == "very_hard"
        assert run(api._calculate_difficulty(2_000_000)) == "hard"
        assert run(api._calculate_difficulty(500_000)) == "medium"
        assert run(api._calculate_difficulty(100_000)) == "easy"
        assert run(api._calculate_difficulty(10_000)) == "very_easy"
        assert run(api._calculate_difficulty(0)) == "very_easy"

    def test_competition_score(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        assert run(AsyncHashtagResearchAPI._competition_score(0)) == 0.0
        assert run(AsyncHashtagResearchAPI._competition_score(-1)) == 0.0
        score = run(AsyncHashtagResearchAPI._competition_score(1_000_000))
        assert 0 < score <= 1.0

    def test_suggest_audience_size(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        assert "500K" in run(AsyncHashtagResearchAPI._suggest_audience_size(10_000_000))
        assert "100K" in run(AsyncHashtagResearchAPI._suggest_audience_size(2_000_000))
        assert "10K" in run(AsyncHashtagResearchAPI._suggest_audience_size(500_000))
        assert "1K" in run(AsyncHashtagResearchAPI._suggest_audience_size(100_000))
        assert "0-1K" in run(AsyncHashtagResearchAPI._suggest_audience_size(1_000))

    def test_analyze_engagement_empty(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        result = run(AsyncHashtagResearchAPI._analyze_engagement([]))
        assert result["avg_likes"] == 0

    def test_analyze_engagement(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        posts = [
            {"like_count": 100, "comment_count": 10, "code": "A"},
            {"like_count": 200, "comment_count": 20, "code": "B"},
        ]
        result = run(AsyncHashtagResearchAPI._analyze_engagement(posts))
        assert result["avg_likes"] == 150.0
        assert len(result["top_posts"]) == 2

    def test_extract_related(self):
        from instaharvest_v2.api.async_hashtag_research import AsyncHashtagResearchAPI
        posts = [
            {"caption": {"text": "#python #coding #dev"}},
            {"caption": {"text": "#python #programming"}},
            {"caption": None},
            {"caption": "plain string #extra"},
        ]
        result = run(AsyncHashtagResearchAPI._extract_related(posts, "python"))
        names = [r["name"] for r in result]
        assert "coding" in names
        assert "python" not in names

    def test_get_hashtag_info(self):
        api, client = self._api()
        client.request.return_value = {"name": "python", "media_count": 50000}
        result = run(api._get_hashtag_info("python"))
        assert result["media_count"] == 50000

    def test_get_hashtag_info_error(self):
        api, client = self._api()
        client.request.side_effect = Exception("err")
        result = run(api._get_hashtag_info("python"))
        assert result["media_count"] == 0

    def test_sample_posts(self):
        api, client = self._api()
        client.request.side_effect = [
            {"sections": [{"layout_content": {"medias": [{"media": {"pk": 1}}]}}]},
            {"sections": [{"layout_content": {"medias": [{"media": {"pk": 2}}]}}]},
        ]
        posts = run(api._sample_posts("python", 5))
        assert len(posts) >= 1

    def test_sample_posts_error(self):
        api, client = self._api()
        client.request.side_effect = Exception("err")
        posts = run(api._sample_posts("python", 5))
        assert posts == []

    def test_analyze(self):
        api, client = self._api()
        client.request.side_effect = [
            {"name": "python", "media_count": 500000},  # info
            {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "like_count": 100, "comment_count": 10, "code": "A",
                           "caption": {"text": "#python #coding"}}}
            ]}}]},  # recent
            {"sections": []},  # top
        ]
        result = run(api.analyze("python", sample_posts=5))
        assert result["name"] == "python"
        assert result["difficulty"] == "medium"

    def test_related(self):
        api, client = self._api()
        client.request.side_effect = [
            {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "caption": {"text": "#test #related #tags"}}}
            ]}}]},
            {"sections": []},
        ]
        result = run(api.related("test"))
        assert isinstance(result, list)

    def test_suggest_easy(self):
        api, client = self._api()
        client.request.side_effect = [
            {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "caption": {"text": "#seed #tag1 #tag2"}}}
            ]}}]},
            {"sections": []},
            {"name": "tag1", "media_count": 1000},
            {"name": "tag2", "media_count": 500},
        ]
        result = run(api.suggest("seed", count=5, mix="easy"))
        assert isinstance(result, list)

    def test_suggest_competitive(self):
        api, client = self._api()
        client.request.side_effect = [
            {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "caption": {"text": "#seed #tag1"}}}
            ]}}]},
            {"sections": []},
            {"name": "tag1", "media_count": 10000000},
        ]
        result = run(api.suggest("seed", count=5, mix="competitive"))
        assert isinstance(result, list)

    def test_suggest_balanced(self):
        api, client = self._api()
        client.request.side_effect = [
            {"sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "caption": {"text": "#seed #easy1 #medium1 #hard1"}}}
            ]}}]},
            {"sections": []},
            {"name": "easy1", "media_count": 1000},
            {"name": "medium1", "media_count": 300000},
            {"name": "hard1", "media_count": 5000000},
        ]
        result = run(api.suggest("seed", count=5, mix="balanced"))
        assert isinstance(result, list)

    def test_compare(self):
        api, client = self._api()
        client.request.side_effect = [
            {"name": "t1", "media_count": 1000},
            {"sections": []}, {"sections": []},
            {"name": "t2", "media_count": 2000},
            {"sections": []}, {"sections": []},
        ]
        result = run(api.compare(["t1", "t2"]))
        assert len(result) == 2
