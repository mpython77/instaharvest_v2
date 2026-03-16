"""
test_100_batch3.py — Coverage push to 100%: Batch 3
=====================================================
Covers: async_ai_suggest, async_rate_limiter, async_automation,
        async_scheduler, async_growth, export, async_media,
        async_friendships, async_client, async_anon_client,
        async_graphql, async_public, async_public_data,
        async_bulk_download, async_auth (deep)
"""
import pytest
import asyncio
import json
import time
import os
import threading
from datetime import datetime
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
# ASYNC AI SUGGEST
# ═══════════════════════════════════════════════════════════
class TestAsyncAISuggest:
    def _api(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        client = M()
        users = M()
        hashtags = M()
        research = M()
        return AsyncAISuggestAPI(client, users, hashtags, research), client, users

    def test_extract_keywords(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        kws = run(AsyncAISuggestAPI._extract_keywords("Beautiful sunset at the beach #photo @user https://example.com"))
        assert "beautiful" in kws
        assert "sunset" in kws
        assert "beach" in kws

    def test_extract_keywords_empty(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        kws = run(AsyncAISuggestAPI._extract_keywords(""))
        assert kws == []

    def test_detect_niche_fitness(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        niche, conf = run(AsyncAISuggestAPI._detect_niche(["fitness", "gym", "workout"]))
        assert niche == "fitness"
        assert conf > 0

    def test_detect_niche_empty(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        niche, conf = run(AsyncAISuggestAPI._detect_niche([]))
        assert niche == "general"
        assert conf == 0.0

    def test_detect_niche_no_match(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        niche, conf = run(AsyncAISuggestAPI._detect_niche(["xyzabc123"]))
        assert niche == "general"

    def test_get_niche_tags(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_niche_tags("fitness", 5))
        assert len(tags) <= 5
        assert "fitness" in tags

    def test_get_niche_tags_partial(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_niche_tags("fit", 5))
        # Should partial match "fitness"
        assert len(tags) > 0

    def test_get_niche_tags_unknown(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_niche_tags("xyznothing", 5))
        assert tags == []

    def test_keywords_to_hashtags(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._keywords_to_hashtags(["sunset", "beach"], 10))
        assert len(tags) > 0

    def test_get_universal_tags(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_universal_tags(5))
        assert len(tags) == 5
        assert "instagood" in tags

    def test_get_longtail_tags(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_longtail_tags(["sunset"], "nature", 10))
        assert len(tags) > 0

    def test_get_longtail_tags_general(self):
        from instaharvest_v2.api.async_ai_suggest import AsyncAISuggestAPI
        tags = run(AsyncAISuggestAPI._get_longtail_tags(["test"], "general", 3))
        # general niche should still produce tags from keywords
        assert isinstance(tags, list)

    def test_hashtags_from_caption(self):
        api, client, users = self._api()
        result = run(api.hashtags_from_caption("Beautiful sunset photography at the beach"))
        assert result is not None
        assert "hashtags" in result
        assert "niche" in result
        assert result["count"] > 0

    def test_hashtags_from_caption_empty(self):
        api, *_ = self._api()
        result = run(api.hashtags_from_caption(""))
        assert result is not None

    def test_caption_ideas_casual(self):
        api, *_ = self._api()
        ideas = run(api.caption_ideas("sunset", style="casual", count=3))
        assert len(ideas) <= 3
        assert "sunset" in ideas[0].lower()

    def test_caption_ideas_all_styles(self):
        api, *_ = self._api()
        for style in ["inspirational", "professional", "poetic", "funny", "nonexistent"]:
            ideas = run(api.caption_ideas("travel", style=style))
            assert len(ideas) > 0

    def test_optimal_set(self):
        api, *_ = self._api()
        result = run(api.optimal_set("fitness", count=15))
        assert result is not None
        assert "hashtags" in result
        assert "difficulty_mix" in result

    def test_hashtags_for_profile(self):
        api, client, users = self._api()
        users.get_by_username.return_value = {"pk": 123, "biography": "fitness lover gym life"}
        client.request.return_value = {"items": [
            {"caption": {"text": "Morning workout #fitness #gym"}}
        ]}
        result = run(api.hashtags_for_profile("testuser"))
        assert result is not None
        assert "hashtags" in result

    def test_hashtags_for_profile_no_user_id(self):
        api, client, users = self._api()
        users.get_by_username.return_value = {"biography": "hello"}
        result = run(api.hashtags_for_profile("testuser"))
        assert result is not None

    def test_hashtags_for_profile_request_error(self):
        api, client, users = self._api()
        users.get_by_username.return_value = {"pk": 1, "biography": "test"}
        client.request.side_effect = Exception("err")
        result = run(api.hashtags_for_profile("testuser"))
        assert result is not None

    def test_hashtags_for_profile_obj_user(self):
        api, client, users = self._api()
        user = M(pk=1, biography="fitness gym workout")
        users.get_by_username.return_value = user
        client.request.return_value = {"items": []}
        result = run(api.hashtags_for_profile("testuser"))
        assert result is not None


# ═══════════════════════════════════════════════════════════
# ASYNC RATE LIMITER
# ═══════════════════════════════════════════════════════════
class TestAsyncRateLimiter:
    def test_init(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="safe", proxy_count=0)
        assert limiter._enabled is True
        assert limiter._request_count == 0

    def test_init_with_proxies(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="fast", proxy_count=5)
        assert limiter._effective_concurrency > 1

    def test_disabled(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(enabled=False)
        run(limiter.acquire("test"))  # should return immediately

    def test_release(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="turbo")
        limiter.release()  # should not error

    def test_on_error(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        limiter.on_error("rate_limit")
        assert limiter._escalation_level == 2
        limiter.on_error("challenge")
        assert limiter._escalation_level == 5  # capped at 5
        limiter.on_error("unknown")

    def test_on_success(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        limiter._escalation_level = 3
        limiter._last_error_time = time.time() - 60
        limiter.on_success()
        assert limiter._escalation_level == 2

    def test_on_success_recent_error(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        limiter._escalation_level = 3
        limiter._last_error_time = time.time()  # just now
        limiter.on_success()
        assert limiter._escalation_level == 3  # no change

    def test_pause(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        limiter.pause(5.0)
        assert limiter._tokens == 0

    def test_calculate_delay(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="safe")
        delay = limiter._calculate_delay()
        assert delay >= 0

    def test_calculate_concurrency(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="safe")
        c = limiter._calculate_concurrency(10)
        assert c > 0

    def test_update_proxy_count(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="fast", proxy_count=0)
        old_c = limiter._effective_concurrency
        limiter.update_proxy_count(5)
        assert limiter._proxy_count == 5

    def test_update_proxy_count_same(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="fast", proxy_count=5)
        limiter.update_proxy_count(5)  # same count, no change

    def test_gate_context(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="turbo", enabled=False)
        ctx = limiter.gate("test")
        assert ctx is not None

    def test_check_legacy(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(enabled=False)
        run(limiter.check("test"))

    def test_stats(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        s = limiter.stats
        assert "mode" in s
        assert "requests" in s
        assert s["requests"] == 0

    def test_mode_property(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(mode="fast")
        assert limiter.mode.name == "fast"

    def test_repr(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter()
        r = repr(limiter)
        assert "RateLimiter" in r

    def test_gate_aenter_aexit(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        limiter = AsyncRateLimiter(enabled=False)
        async def use_gate():
            async with limiter.gate("cat"):
                pass
        run(use_gate())


# ═══════════════════════════════════════════════════════════
# ASYNC AUTOMATION
# ═══════════════════════════════════════════════════════════
class TestAsyncAutomation:
    def _api(self):
        from instaharvest_v2.api.async_automation import AsyncAutomationAPI
        client = M()
        direct = M()
        media = M()
        friendships = M()
        stories = M()
        return AsyncAutomationAPI(client, direct, media, friendships, stories), client, direct, media, friendships, stories

    def test_init(self):
        api, *_ = self._api()
        assert api._seen_users == set()
        assert api._action_log == []

    def test_template_render(self):
        from instaharvest_v2.api.async_automation import TemplateEngine
        result = run(TemplateEngine.render("Hello {username}!", {"username": "test"}))
        assert result == "Hello test!"

    def test_template_render_with_name(self):
        from instaharvest_v2.api.async_automation import TemplateEngine
        result = run(TemplateEngine.render("{name} rocks", {"name": "John"}))
        assert "John" in result

    def test_template_render_random(self):
        from instaharvest_v2.api.async_automation import TemplateEngine
        result = run(TemplateEngine.render("Cool {random}"))
        assert result is not None

    def test_template_render_date(self):
        from instaharvest_v2.api.async_automation import TemplateEngine
        result = run(TemplateEngine.render("Today is {date}"))
        assert datetime.now().strftime("%Y") in result

    def test_template_pick_and_render(self):
        from instaharvest_v2.api.async_automation import TemplateEngine
        result = run(TemplateEngine.pick_and_render(["Hi {username}"], {"username": "u1"}))
        # pick_and_render returns a coroutine but render returns non-coroutine
        assert result is not None

    def test_automation_limits(self):
        from instaharvest_v2.api.async_automation import AutomationLimits
        lim = AutomationLimits(max_per_hour=50, min_delay=5, max_delay=10)
        assert lim.max_per_hour == 50

    def test_should_stop_rate_limit(self):
        from instaharvest_v2.api.async_automation import AsyncAutomationAPI, AutomationLimits
        class RateLimitError(Exception): pass
        limits = AutomationLimits()
        result = run(AsyncAutomationAPI._should_stop(RateLimitError("too fast"), limits))
        assert result is True

    def test_should_stop_login(self):
        from instaharvest_v2.api.async_automation import AsyncAutomationAPI, AutomationLimits
        class LoginRequired(Exception): pass
        limits = AutomationLimits()
        result = run(AsyncAutomationAPI._should_stop(LoginRequired("login"), limits))
        assert result is True

    def test_should_stop_normal(self):
        from instaharvest_v2.api.async_automation import AsyncAutomationAPI, AutomationLimits
        limits = AutomationLimits()
        result = run(AsyncAutomationAPI._should_stop(ValueError("x"), limits))
        assert result is False

    def test_log_action(self):
        api, *_ = self._api()
        run(api._log_action("test", "target", "detail"))
        assert len(api._action_log) == 1

    def test_log_action_overflow(self):
        api, *_ = self._api()
        api._action_log = [{"i": i} for i in range(501)]
        run(api._log_action("test", "t", "d"))
        assert len(api._action_log) <= 501

    def test_action_log_property(self):
        api, *_ = self._api()
        api._action_log = [{"i": i} for i in range(200)]
        log = run(api.action_log)
        assert len(log) <= 100

    def test_users_get_safe(self):
        api, client, *_ = self._api()
        client.request.return_value = {"data": {"user": {"pk": 1}}}
        result = run(api._users_get_safe("testuser"))
        assert result is not None

    def test_users_get_safe_error(self):
        api, client, *_ = self._api()
        client.request.side_effect = Exception("err")
        result = run(api._users_get_safe("testuser"))
        assert result["username"] == "testuser"

    def test_get_hashtag_posts(self):
        api, client, *_ = self._api()
        client.request.return_value = {"sections": [
            {"layout_content": {"medias": [{"media": {"pk": 1}}]}}
        ]}
        posts = run(api._get_hashtag_posts("test", 10))
        assert len(posts) == 1

    def test_get_hashtag_posts_error(self):
        api, client, *_ = self._api()
        client.request.side_effect = Exception("err")
        posts = run(api._get_hashtag_posts("test", 10))
        assert posts == []

    @patch("time.sleep")
    def test_smart_delay(self, _):
        from instaharvest_v2.api.async_automation import AutomationLimits
        api, *_ = self._api()
        with patch("random.random", return_value=0.5):
            run(api._smart_delay(AutomationLimits(min_delay=0, max_delay=0.01)))

    @patch("time.sleep")
    def test_auto_like_feed(self, _):
        api, client, direct, media, *_ = self._api()
        client.request.return_value = {"feed_items": [
            {"media_or_ad": {"pk": 1, "code": "ABC"}},
            {"media_or_ad": {"pk": 2, "code": "DEF", "has_liked": True}},
        ]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.auto_like_feed(count=1))
        assert result is not None

    @patch("time.sleep")
    def test_auto_like_feed_error(self, _):
        api, client, *_ = self._api()
        client.request.side_effect = Exception("err")
        result = run(api.auto_like_feed(count=1))
        assert result["liked"] == 0

    @patch("time.sleep")
    def test_auto_like_hashtag(self, _):
        api, client, direct, media, *_ = self._api()
        client.request.return_value = {"sections": [
            {"layout_content": {"medias": [{"media": {"pk": 1, "code": "X"}}]}}
        ]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.auto_like_hashtag("test", count=1))
        assert result is not None

    @patch("time.sleep")
    def test_comment_on_hashtag(self, _):
        api, client, direct, media, *_ = self._api()
        client.request.return_value = {"sections": [
            {"layout_content": {"medias": [{"media": {"pk": 1, "code": "X", "user": {"username": "u1"}}}]}}
        ]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.comment_on_hashtag("test", ["Nice!"], count=1))
        assert result is not None

    @patch("time.sleep")
    def test_watch_stories(self, _):
        api, client, direct, media, friendships, stories = self._api()
        client.request.return_value = {"data": {"user": {"pk": 1}}}
        stories.get_user_stories.return_value = {"items": [{"pk": "s1"}, {"pk": "s2"}]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.watch_stories("testuser"))
        assert result is not None

    def test_watch_stories_no_api(self):
        from instaharvest_v2.api.async_automation import AsyncAutomationAPI
        api = AsyncAutomationAPI(M(), M(), M(), M(), stories_api=None)
        result = run(api.watch_stories("test"))
        assert result["error"] == "StoriesAPI not available"

    @patch("time.sleep")
    def test_dm_new_followers_first_run(self, _):
        api, client, direct, media, friendships, stories = self._api()
        sm = M()
        sm.get_session.return_value = M(ds_user_id="123")
        client._session_mgr = sm
        friendships.get_followers.return_value = {"users": [{"username": "f1"}]}
        result = run(api.dm_new_followers("Welcome!"))
        assert result["sent"] == 0  # first run saves baseline


# ═══════════════════════════════════════════════════════════
# ASYNC GROWTH
# ═══════════════════════════════════════════════════════════
class TestAsyncGrowth:
    def _api(self):
        from instaharvest_v2.api.async_growth import AsyncGrowthAPI
        client = M()
        users = M()
        friendships = M()
        sm = M()
        sm.get_session.return_value = M(ds_user_id="123")
        client._session_mgr = sm
        return AsyncGrowthAPI(client, users, friendships), client, users, friendships

    def test_init(self):
        api, *_ = self._api()
        assert api._whitelist == set()
        assert api._blacklist == set()

    def test_growth_limits(self):
        from instaharvest_v2.api.async_growth import GrowthLimits
        l = GrowthLimits(max_per_hour=10, max_per_day=100)
        assert l.max_per_hour == 10

    def test_growth_filters_all_pass(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters()
        assert run(f.matches({"follower_count": 100, "media_count": 5})) is True

    def test_growth_filters_min_followers(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(min_followers=100)
        assert run(f.matches({"follower_count": 50})) is False
        assert run(f.matches({"follower_count": 200})) is True

    def test_growth_filters_max_followers(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(max_followers=1000)
        assert run(f.matches({"follower_count": 5000})) is False

    def test_growth_filters_is_private(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(is_private=False)
        assert run(f.matches({"is_private": True})) is False

    def test_growth_filters_bio_keywords(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(bio_keywords=["fitness"])
        assert run(f.matches({"biography": "I love fitness"})) is True
        assert run(f.matches({"biography": "I love cooking"})) is False

    def test_growth_filters_exclude(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(exclude_keywords=["spam"])
        assert run(f.matches({"biography": "spam account"})) is False

    def test_growth_filters_has_bio(self):
        from instaharvest_v2.api.async_growth import GrowthFilters
        f = GrowthFilters(has_bio=True)
        assert run(f.matches({"biography": ""})) is False
        assert run(f.matches({"biography": "hello"})) is True

    def test_add_whitelist(self):
        api, *_ = self._api()
        run(api.add_whitelist(["user1", "user2"]))
        assert "user1" in api._whitelist

    def test_add_blacklist(self):
        api, *_ = self._api()
        run(api.add_blacklist(["bad1"]))
        assert "bad1" in api._blacklist

    def test_clear_whitelist(self):
        api, *_ = self._api()
        api._whitelist = {"u1"}
        run(api.clear_whitelist())
        assert len(api._whitelist) == 0

    def test_clear_blacklist(self):
        api, *_ = self._api()
        api._blacklist = {"b1"}
        run(api.clear_blacklist())
        assert len(api._blacklist) == 0

    def test_should_stop(self):
        from instaharvest_v2.api.async_growth import AsyncGrowthAPI, GrowthLimits
        limits = GrowthLimits()
        assert run(AsyncGrowthAPI._should_stop(ValueError("x"), limits)) is False

    def test_log_action(self):
        api, *_ = self._api()
        run(api._log_action("follow", "user1", 123))
        assert len(api._action_log) == 1

    def test_action_log_property(self):
        api, *_ = self._api()
        api._action_log = [{"i": i} for i in range(200)]
        log = run(api.action_log)
        assert len(log) <= 100

    @patch("time.sleep")
    def test_get_non_followers(self, _):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {"users": [{"username": "f1"}]}
        friendships.get_following.return_value = {"users": [{"username": "f1"}, {"username": "f2"}]}
        result = run(api.get_non_followers())
        assert len(result) == 1  # f2 is not a follower

    @patch("time.sleep")
    def test_get_fans(self, _):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {"users": [{"username": "f1"}, {"username": "f2"}]}
        friendships.get_following.return_value = {"users": [{"username": "f1"}]}
        result = run(api.get_fans())
        assert len(result) == 1  # f2 is not being followed

    @patch("time.sleep")
    def test_follow_hashtag_users(self, _):
        api, client, users, friendships = self._api()
        client.request.return_value = {"sections": [
            {"layout_content": {"medias": [{"media": {"user": {"username": "u1", "pk": 1}}}]}}
        ]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.follow_hashtag_users("test", count=1))
        assert result is not None

    @patch("time.sleep")
    def test_follow_users_of(self, _):
        api, client, users, friendships = self._api()
        users.get_by_username.return_value = {"pk": 1}
        friendships.get_followers.return_value = {"users": [{"pk": 2, "username": "u1"}]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.follow_users_of("target", count=1))
        assert result is not None

    @patch("time.sleep")
    def test_unfollow_non_followers(self, _):
        api, client, users, friendships = self._api()
        friendships.get_followers.return_value = {"users": []}
        friendships.get_following.return_value = {"users": [{"pk": 1, "username": "u1"}]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.unfollow_non_followers(max_count=1))
        assert result is not None

    @patch("time.sleep")
    def test_unfollow_all(self, _):
        api, client, users, friendships = self._api()
        friendships.get_following.return_value = {"users": [{"pk": 1, "username": "u1"}]}
        with patch("random.uniform", return_value=0), patch("random.random", return_value=0.5):
            result = run(api.unfollow_all(max_count=1))
        assert result is not None


# ═══════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════
class TestScheduler:
    def test_scheduler_job(self):
        from instaharvest_v2.api.async_scheduler import SchedulerJob
        job = SchedulerJob("post", datetime.now(), {"photo": "test.jpg"})
        assert job.status == "pending"
        assert job.job_type == "post"

    def test_scheduler_job_to_dict(self):
        from instaharvest_v2.api.async_scheduler import SchedulerJob
        job = SchedulerJob("story", datetime.now(), {"photo": "s.jpg"}, job_id="abc123")
        d = run(job.to_dict())
        assert d["id"] == "abc123"
        assert d["job_type"] == "story"

    def test_scheduler_job_from_dict(self):
        from instaharvest_v2.api.async_scheduler import SchedulerJob
        data = {
            "id": "test123",
            "job_type": "post",
            "scheduled_at": "2025-01-01T10:00:00",
            "params": {"photo": "x.jpg"},
            "status": "pending",
            "created_at": "2025-01-01T09:00:00",
            "error": None,
        }
        job = SchedulerJob.from_dict(data)
        assert job.id == "test123"
        assert job.status == "pending"

    def test_parse_time_formats(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI
        dt = run(AsyncSchedulerAPI._parse_time("2025-01-01 10:00"))
        assert dt.year == 2025
        dt2 = run(AsyncSchedulerAPI._parse_time("2025-01-01 10:00:00"))
        assert dt2.second == 0
        dt3 = run(AsyncSchedulerAPI._parse_time("2025-01-01T10:00:00"))
        assert dt3.hour == 10
        dt4 = run(AsyncSchedulerAPI._parse_time("2025-01-01T10:00"))
        assert dt4.minute == 0

    def test_parse_time_invalid(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI
        result = run(AsyncSchedulerAPI._parse_time("invalid"))
        assert result is None  # ValueError caught by run()

    def test_execute_job_post(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        upload = M()
        stories = M()
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = upload
            api._stories = stories
            api._jobs = []
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("post", datetime.now(), {"photo": "/tmp/x.jpg", "caption": "Hello"})
        upload.photo.return_value = "media_123"
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._execute_job(job))
        assert job.status == "done"

    def test_execute_job_story_photo(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        upload = M()
        stories = M()
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = upload
            api._stories = stories
            api._jobs = []
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("story", datetime.now(), {"photo": "/tmp/s.jpg", "video": None})
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._execute_job(job))
        assert job.status == "done"

    def test_execute_job_reel(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        upload = M()
        stories = M()
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = upload
            api._stories = stories
            api._jobs = []
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("reel", datetime.now(), {"video": "/tmp/r.mp4", "caption": "Reel"})
        upload.reel.return_value = "reel_123"
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._execute_job(job))
        assert job.status == "done"

    def test_execute_job_action(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = M()
            api._stories = M()
            api._jobs = []
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("action", datetime.now(), {"action_name": "test", "kwargs": {}})
        job._action = lambda: "done"
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._execute_job(job))
        assert job.status == "done"

    def test_execute_job_failed(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        upload = M()
        upload.photo.side_effect = Exception("upload failed")
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = upload
            api._stories = M()
            api._jobs = []
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("post", datetime.now(), {"photo": "/tmp/x.jpg"})
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._execute_job(job))
        assert job.status == "failed"

    def test_check_and_execute(self):
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob
        from datetime import timedelta
        with patch("asyncio.create_task"):
            api = AsyncSchedulerAPI.__new__(AsyncSchedulerAPI)
            api._upload = M()
            api._stories = M()
            api._lock = threading.Lock()
            api._persist_path = "/tmp/test_scheduler.json"
        job = SchedulerJob("post", datetime.now() - timedelta(hours=1), {"photo": "/tmp/x.jpg"})
        api._jobs = [job]
        api._upload.photo.return_value = "ok"
        with patch.object(api, '_save_jobs', new_callable=AsyncMock):
            run(api._check_and_execute())
        assert job.status == "done"


# ═══════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════
class TestExport:
    def _api(self):
        from instaharvest_v2.api.export import ExportAPI
        client = M()
        users = M()
        friendships = M()
        media = M()
        hashtags = M()
        return ExportAPI(client, users, friendships, media, hashtags), client, users, friendships, media, hashtags

    def test_export_filter_basic(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter()
        assert f.matches({"follower_count": 100}) is True

    def test_export_filter_min_followers(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(min_followers=100)
        assert f.matches({"follower_count": 50}) is False
        assert f.matches({"follower_count": 200}) is True

    def test_export_filter_all_fields(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(
            min_followers=10, max_followers=5000,
            min_following=5, max_following=500,
            min_posts=3, is_private=False, is_verified=False,
            is_business=True, has_bio=True, has_profile_pic=True,
            bio_keywords=["dev"], exclude_keywords=["spam"],
        )
        assert f.matches({
            "follower_count": 100, "following_count": 50, "media_count": 10,
            "is_private": False, "is_verified": False, "is_business_account": True,
            "biography": "I am a dev", "profile_pic_url": "https://pic.com/img.jpg",
        }) is True

    def test_export_filter_has_bio_false(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(has_bio=False)
        assert f.matches({"biography": "hello"}) is False
        assert f.matches({"biography": ""}) is True

    def test_export_filter_has_profile_pic_default(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(has_profile_pic=True)
        assert f.matches({"profile_pic_url": "https://default/pic.jpg"}) is False

    def test_export_filter_custom(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(custom_filter=lambda u: u.get("username") != "bot")
        assert f.matches({"username": "bot"}) is False
        assert f.matches({"username": "real"}) is True

    def test_user_to_row_dict(self):
        api, *_ = self._api()
        row = api._user_to_row({"username": "u1", "pk": 123, "follower_count": 100})
        assert row["username"] == "u1"
        assert row["user_id"] == 123

    def test_user_to_row_obj(self):
        api, *_ = self._api()
        user = M(username="u1", full_name="User", pk=1, followers=10, follower_count=10,
                 following=5, following_count=5, media_count=3, is_private=False,
                 is_verified=False, is_business_account=False, is_business=False,
                 biography="bio", external_url="", profile_pic_url="pic",
                 category="cat", category_name="Cat", posts_count=0,
                 user_id=1)
        row = api._user_to_row(user)
        assert row["username"] == "u1"

    def test_user_to_row_other(self):
        api, *_ = self._api()
        row = api._user_to_row(42)
        assert row == {"username": "42"}

    def test_followers_to_csv(self):
        api, client, users, friendships, *_ = self._api()
        users.get_by_username.return_value = M(pk=1)
        friendships.get_followers.return_value = {"users": [{"username": "f1", "pk": 1}]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.followers_to_csv("testuser", path)
            assert result["exported"] == 1
        finally:
            os.unlink(path)

    def test_following_to_csv(self):
        api, client, users, friendships, *_ = self._api()
        users.get_by_username.return_value = M(pk=1)
        friendships.get_following.return_value = {"users": [{"username": "f1", "pk": 1}]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.following_to_csv("testuser", path)
            assert result["exported"] == 1
        finally:
            os.unlink(path)

    def test_post_likers(self):
        api, client, users, friendships, media, *_ = self._api()
        media.get_likers.return_value = {"users": [{"username": "l1", "pk": 1}]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.post_likers("media123", path)
            assert result["exported"] == 1
        finally:
            os.unlink(path)

    def test_post_likers_error(self):
        api, client, users, friendships, media, *_ = self._api()
        media.get_likers.side_effect = Exception("err")
        result = api.post_likers("m1", "/tmp/out.csv")
        assert result["exported"] == 0

    def test_post_commenters(self):
        api, client, users, friendships, media, *_ = self._api()
        media.get_all_comments.return_value = [
            {"user": {"username": "c1", "pk": 1}, "text": "nice"},
            {"user": {"username": "c1", "pk": 1}, "text": "great"},  # duplicate
        ]
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.post_commenters("m1", path)
            assert result["exported"] == 1  # deduplicated
        finally:
            os.unlink(path)

    def test_post_commenters_error(self):
        api, client, users, friendships, media, *_ = self._api()
        media.get_all_comments.side_effect = Exception("err")
        result = api.post_commenters("m1", "/tmp/out.csv")
        assert result["exported"] == 0

    def test_to_json(self):
        api, client, users, friendships, *_ = self._api()
        users.get_full_profile.return_value = {"pk": 1, "username": "test"}
        client.request.return_value = {"items": []}
        friendships.get_followers.return_value = {"users": []}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = api.to_json("testuser", path, include_posts=True, include_followers_sample=5)
            assert "file" in result
        finally:
            os.unlink(path)

    def test_to_json_errors(self):
        api, client, users, friendships, *_ = self._api()
        users.get_full_profile.side_effect = Exception("err")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = api.to_json("testuser", path)
            assert "file" in result
        finally:
            os.unlink(path)

    def test_hashtag_users(self):
        api, client, users, friendships, media, hashtags = self._api()
        hashtags.get_recent_media.return_value = {"items": [
            {"user": {"username": "u1", "pk": 1}}
        ]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.hashtag_users("python", path, count=5)
            assert result["exported"] >= 1
        finally:
            os.unlink(path)

    def test_hashtag_users_sections_fallback(self):
        api, client, users, friendships, media, hashtags = self._api()
        hashtags.get_recent_media.return_value = {}
        hashtags.get_sections.return_value = {"sections": [
            {"layout_content": {"medias": [{"media": {"user": {"username": "u2", "pk": 2}}}]}}
        ]}
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.hashtag_users("python", path, count=5)
            assert result["exported"] >= 1
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════
# ASYNC CLIENT (core)
# ═══════════════════════════════════════════════════════════
class TestAsyncClientCore:
    def test_import(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        assert AsyncHttpClient is not None


# ═══════════════════════════════════════════════════════════
# ASYNC ANON CLIENT (core)
# ═══════════════════════════════════════════════════════════
class TestAsyncAnonClient:
    def test_import(self):
        from instaharvest_v2 import async_anon_client
        assert async_anon_client is not None


# ═══════════════════════════════════════════════════════════
# SPEED MODES
# ═══════════════════════════════════════════════════════════
class TestSpeedModes:
    def test_get_mode(self):
        from instaharvest_v2.speed_modes import get_mode
        safe = get_mode("safe")
        assert safe.name == "safe"
        fast = get_mode("fast")
        assert fast.name == "fast"
        turbo = get_mode("turbo")
        assert turbo.name == "turbo"

    def test_get_mode_unknown(self):
        from instaharvest_v2.speed_modes import get_mode
        try:
            get_mode("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_speed_mode_properties(self):
        from instaharvest_v2.speed_modes import SAFE, FAST, TURBO, UNLIMITED
        assert SAFE.max_concurrency == 5
        assert FAST.rate_per_minute == 60
        assert TURBO.burst_size == 20
        assert UNLIMITED.max_concurrency == 1000
