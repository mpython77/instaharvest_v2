"""
test_automation_analytics_audience.py — Deep Coverage for 3 Major APIs
=======================================================================
AutomationAPI (218×2 miss), AnalyticsAPI (187×2 miss), AudienceAPI (180×2 miss)
All method bodies executed via MagicMock chain. ~650 miss lines targeted.
"""
import pytest
import time as _time
from unittest.mock import MagicMock, patch

M = MagicMock


# ═══════════════════════════════════════════════════════════
# AutomationLimits + TemplateEngine
# ═══════════════════════════════════════════════════════════
class TestAutomationLimits:
    def test_defaults(self):
        from instaharvest_v2.api.automation import AutomationLimits
        al = AutomationLimits()
        assert al.max_per_hour == 30
        assert al.min_delay == 15.0
        assert al.stop_on_challenge is True

    def test_custom(self):
        from instaharvest_v2.api.automation import AutomationLimits
        al = AutomationLimits(max_per_hour=5, min_delay=1.0, max_delay=2.0, stop_on_challenge=False, stop_on_rate_limit=False)
        assert al.max_per_hour == 5
        assert al.stop_on_challenge is False


class TestTemplateEngine:
    def test_render_username(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.render("Hello {username}!", {"username": "testuser"})
        assert "testuser" in r

    def test_render_name(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.render("Hi {name}", {"name": "John", "username": "john"})
        assert "John" in r

    def test_render_random(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.render("Great {random}")
        assert len(r) > 5

    def test_render_date(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.render("Today is {date}")
        assert "202" in r

    def test_pick_and_render(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.pick_and_render(["Hi {username}", "Hey {username}"], {"username": "test"})
        assert "test" in r

    def test_emojis_list(self):
        from instaharvest_v2.api.automation import TemplateEngine
        assert len(TemplateEngine.EMOJIS) >= 5


# ═══════════════════════════════════════════════════════════
# AutomationAPI — deep method body coverage
# ═══════════════════════════════════════════════════════════
class TestAutomationAPIDeep:
    def _make(self):
        from instaharvest_v2.api.automation import AutomationAPI
        mc = M()
        sm = M()
        sess = M()
        sess.ds_user_id = "999"
        sm.get_session.return_value = sess
        mc._session_mgr = sm
        return AutomationAPI(mc, M(), M(), M(), M())

    def test_init(self):
        api = self._make()
        assert api._seen_users == set()
        assert api._known_followers == set()

    def test_action_log_property(self):
        api = self._make()
        assert api.action_log == []

    def test_log_action(self):
        api = self._make()
        api._log_action("test", "target", "detail")
        assert len(api._action_log) == 1

    def test_log_action_overflow(self):
        api = self._make()
        for i in range(600):
            api._log_action("test", f"t{i}", "d")
        assert len(api._action_log) == 500

    def test_should_stop_rate_limit(self):
        from instaharvest_v2.api.automation import AutomationAPI, AutomationLimits
        class RateLimitError(Exception): pass
        assert AutomationAPI._should_stop(RateLimitError(), AutomationLimits()) is True

    def test_should_stop_challenge(self):
        from instaharvest_v2.api.automation import AutomationAPI, AutomationLimits
        class ChallengeRequired(Exception): pass
        assert AutomationAPI._should_stop(ChallengeRequired(), AutomationLimits()) is True

    def test_should_not_stop(self):
        from instaharvest_v2.api.automation import AutomationAPI, AutomationLimits
        assert AutomationAPI._should_stop(ValueError("test"), AutomationLimits()) is False

    @patch('time.sleep')
    def test_smart_delay(self, _):
        from instaharvest_v2.api.automation import AutomationLimits
        api = self._make()
        api._smart_delay(AutomationLimits(min_delay=0.001, max_delay=0.002))

    def test_users_get_safe(self):
        api = self._make()
        api._client.request.return_value = {"data": {"user": {"pk": 1, "username": "test"}}}
        result = api._users_get_safe("test")
        assert result["username"] == "test"

    def test_users_get_safe_error(self):
        api = self._make()
        api._client.request.side_effect = Exception("network")
        result = api._users_get_safe("test")
        assert result["username"] == "test"

    def test_get_followers_set(self):
        api = self._make()
        api._friendships.get_followers.return_value = {
            "users": [{"username": "u1"}, {"username": "u2"}], "next_max_id": None
        }
        s = api._get_followers_set("999")
        assert "u1" in s and "u2" in s

    def test_get_hashtag_posts(self):
        api = self._make()
        api._client.request.return_value = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "code": "abc", "user": {"username": "u1"}}}
            ]}}]
        }
        posts = api._get_hashtag_posts("fashion", 10)
        assert len(posts) == 1

    @patch('time.sleep')
    def test_dm_new_followers_first_run(self, _):
        """First run should save baseline."""
        api = self._make()
        api._friendships.get_followers.return_value = {
            "users": [{"username": "f1"}, {"username": "f2"}], "next_max_id": None
        }
        result = api.dm_new_followers("Hello {username}!")
        assert result["sent"] == 0
        assert "First run" in result.get("note", "")

    @patch('time.sleep')
    def test_dm_new_followers_second_run(self, _):
        """Second run should detect new followers and DM."""
        api = self._make()
        api._known_followers = {"f1", "f2"}
        api._friendships.get_followers.return_value = {
            "users": [{"username": "f1"}, {"username": "f2"}, {"username": "f3"}],
            "next_max_id": None
        }
        api._client.request.return_value = {"data": {"user": {"pk": 3, "username": "f3", "full_name": "New"}}}
        api._direct.send_text.return_value = {"status": "ok"}
        result = api.dm_new_followers(["Hey {username}!", "Welcome {name}!"], max_count=1)
        assert result["sent"] == 1
        assert result["new_followers_found"] >= 1

    @patch('time.sleep')
    def test_comment_on_hashtag(self, _):
        api = self._make()
        api._client.request.return_value = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"pk": 100, "code": "abc", "user": {"username": "owner1", "full_name": "Owner"}}}
            ]}}]
        }
        api._media.comment.return_value = {"status": "ok"}
        result = api.comment_on_hashtag("fashion", ["Nice {random}!", "Cool!"], count=1)
        assert result["commented"] == 1

    @patch('time.sleep')
    def test_auto_like_feed(self, _):
        api = self._make()
        api._client.request.return_value = {
            "feed_items": [
                {"media_or_ad": {"pk": 1, "code": "abc", "has_liked": False}},
                {"media_or_ad": {"pk": 2, "code": "def", "has_liked": True}},
            ]
        }
        api._media.like.return_value = {"status": "ok"}
        result = api.auto_like_feed(count=1)
        assert result["liked"] == 1

    @patch('time.sleep')
    def test_auto_like_hashtag(self, _):
        api = self._make()
        api._client.request.return_value = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"pk": 1, "code": "xyz", "has_liked": False, "user": {"username": "u1"}}}
            ]}}]
        }
        api._media.like.return_value = {"status": "ok"}
        result = api.auto_like_hashtag("python", count=1)
        assert result["liked"] == 1

    @patch('time.sleep')
    def test_watch_stories(self, _):
        api = self._make()
        api._client.request.return_value = {"data": {"user": {"pk": 123}}}
        api._stories.get_user_stories.return_value = {
            "items": [{"pk": 1}, {"pk": 2}]
        }
        api._stories.mark_seen.return_value = {"status": "ok"}
        result = api.watch_stories("testuser")
        assert result["watched"] == 2

    def test_watch_stories_no_api(self):
        from instaharvest_v2.api.automation import AutomationAPI
        api = AutomationAPI(M(), M(), M(), M(), stories_api=None)
        result = api.watch_stories("test")
        assert result["watched"] == 0


# ═══════════════════════════════════════════════════════════
# AnalyticsAPI — deep method body coverage
# ═══════════════════════════════════════════════════════════
class TestAnalyticsAPIDeep:
    def _make(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        return AnalyticsAPI(M(), M(), M(), M())

    def _posts(self, n=3):
        import time
        now = int(time.time())
        return [
            {"pk": i, "code": f"C{i}", "like_count": 100*(i+1), "comment_count": 10*(i+1),
             "media_type": [1,2,8][i%3], "taken_at": now - 86400*i,
             "caption": {"text": f"Post {i} #fashion #beauty"}, "user": {"username": f"u{i}"}}
            for i in range(n)
        ]

    def test_get_likes(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_likes({"like_count": 100}) == 100
        assert AnalyticsAPI._get_likes({"likes": 50}) == 50
        assert AnalyticsAPI._get_likes({}) == 0

    def test_get_comments(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_comments({"comment_count": 10}) == 10

    def test_get_timestamp(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_timestamp({"taken_at": 1000}) == 1000

    def test_get_caption_dict(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_caption({"caption": {"text": "hello"}}) == "hello"

    def test_get_caption_str(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_caption({"caption": "direct"}) == "direct"

    def test_get_media_type(self):
        from instaharvest_v2.api.analytics import AnalyticsAPI
        assert AnalyticsAPI._get_media_type({"media_type": 1}) == "photo"
        assert AnalyticsAPI._get_media_type({"media_type": 2}) == "video"
        assert AnalyticsAPI._get_media_type({"media_type": 8}) == "carousel"
        assert AnalyticsAPI._get_media_type({"__typename": "GraphVideo"}) == "video"
        assert AnalyticsAPI._get_media_type({"__typename": "GraphSidecar"}) == "carousel"
        assert AnalyticsAPI._get_media_type({}) == "photo"

    def test_fetch_posts(self):
        api = self._make()
        api._client.request.return_value = {
            "items": self._posts(3), "more_available": False
        }
        posts = api._fetch_posts("123", 3)
        assert len(posts) == 3

    def test_fetch_posts_no_user_id(self):
        api = self._make()
        assert api._fetch_posts(None, 5) == []

    def test_engagement_rate(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123, "followers": 10000, "follower_count": 10000}
        api._client.request.return_value = {"items": self._posts(3), "more_available": False}
        result = api.engagement_rate("testuser", 3)
        assert "engagement_rate" in result
        assert result["posts_analyzed"] == 3
        assert result["rating"] in ("excellent", "very_good", "good", "average", "low")
        assert result["followers"] == 10000

    def test_engagement_rate_no_posts(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123, "followers": 1000}
        api._client.request.return_value = {"items": [], "more_available": False}
        result = api.engagement_rate("testuser")
        assert result["rating"] == "no_data"

    def test_best_posting_times(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123, "followers": 5000, "follower_count": 5000}
        api._client.request.return_value = {"items": self._posts(5), "more_available": False}
        result = api.best_posting_times("testuser", 5)
        assert "best_hours" in result
        assert "best_days" in result
        assert "hourly_breakdown" in result

    def test_best_posting_times_no_posts(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._client.request.return_value = {"items": []}
        result = api.best_posting_times("testuser")
        assert result["best_hours"] == []

    def test_content_analysis(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123, "followers": 5000, "follower_count": 5000}
        api._client.request.return_value = {"items": self._posts(5), "more_available": False}
        result = api.content_analysis("testuser", 5)
        assert "media_type_breakdown" in result
        assert "top_posts" in result
        assert "posting_frequency" in result
        assert result["posts_analyzed"] == 5

    def test_profile_summary(self):
        api = self._make()
        user = M()
        user.username = "test"; user.full_name = "Test"; user.followers = 5000
        user.following = 200; user.is_verified = False; user.is_private = False
        user.biography = "bio"; user.pk = 123; user.follower_count = 5000
        api._users.get_by_username.return_value = user
        api._client.request.return_value = {"items": self._posts(3), "more_available": False}
        result = api.profile_summary("test", 3)
        assert "profile" in result
        assert "engagement" in result
        assert "best_times" in result
        assert "content" in result

    def test_compare(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123, "followers": 5000, "follower_count": 5000}
        api._client.request.return_value = {"items": self._posts(3), "more_available": False}
        result = api.compare(["user1", "user2"], 3)
        assert "accounts" in result
        assert "rankings" in result
        assert "winner" in result
        assert len(result["accounts"]) == 2


# ═══════════════════════════════════════════════════════════
# AudienceAPI — deep method body coverage
# ═══════════════════════════════════════════════════════════
class TestAudienceAPIDeep:
    def _make(self):
        from instaharvest_v2.api.audience import AudienceAPI
        return AudienceAPI(M(), M(), M())

    def test_audience_quality_score(self):
        from instaharvest_v2.api.audience import AudienceAPI
        assert AudienceAPI._audience_quality_score(0.1, 0.2, 1000, 20) == "excellent"
        assert AudienceAPI._audience_quality_score(0.01, 0.5, 100, 5) == "low"
        assert AudienceAPI._audience_quality_score(0.1, 0.3, 600, 5) == "excellent"  # verified+private+followers = 6
        assert AudienceAPI._audience_quality_score(0.0, 0.5, 100, 15) == "average"  # posts only = 2

    def test_score_candidates(self):
        from instaharvest_v2.api.audience import AudienceAPI
        cands = {
            "u1": {"username": "u1", "followers": 5000, "weight": 3, "is_verified": True},
            "u2": {"username": "u2", "followers": 200, "weight": 1, "is_verified": False},
            "source": {"username": "source", "followers": 1000, "weight": 5},
        }
        scored = AudienceAPI._score_candidates(cands, "source")
        assert len(scored) == 2  # source excluded
        assert any(s["username"] == "u1" for s in scored)

    def test_get_follower_set(self):
        api = self._make()
        api._friendships.get_followers.return_value = {
            "users": [{"username": "u1"}, {"username": "u2"}], "next_max_id": None
        }
        s = api._get_follower_set("123", 10)
        assert "u1" in s

    def test_get_followers_list(self):
        api = self._make()
        api._friendships.get_followers.return_value = {
            "users": [{"username": "u1", "pk": 1}], "next_max_id": None
        }
        lst = api._get_followers_list("123", 5)
        assert len(lst) == 1

    def test_get_user_hashtags(self):
        api = self._make()
        api._client.request.return_value = {
            "items": [{"caption": {"text": "Hello #fashion #beauty #style"}}]
        }
        tags = api._get_user_hashtags("123")
        assert "fashion" in tags

    @patch('time.sleep')
    def test_discover_via_followers(self, _):
        api = self._make()
        api._friendships.get_followers.return_value = {
            "users": [{"pk": 1, "username": "f1"}], "next_max_id": None
        }
        api._friendships.get_following.return_value = {
            "users": [{"pk": 2, "username": "candidate1", "follower_count": 500, "is_private": False, "full_name": "C1", "is_verified": False}]
        }
        candidates = {}
        api._discover_via_followers("123", candidates, 10, 100, 50000, True)
        assert "candidate1" in candidates

    def test_discover_via_hashtags(self):
        api = self._make()
        api._client.request.side_effect = [
            {"items": [{"caption": {"text": "#fashion #style"}}]},  # _get_user_hashtags
            {"sections": [{"layout_content": {"medias": [
                {"media": {"user": {"pk": 3, "username": "htag_user", "follower_count": 1000, "is_private": False, "full_name": "HU", "is_verified": False}}}
            ]}}]},
        ]
        candidates = {}
        api._discover_via_hashtags("123", "source_user", candidates, 5, 100, 50000, True)
        assert "htag_user" in candidates

    @patch('time.sleep')
    def test_find_lookalike_mixed(self, _):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._friendships.get_followers.return_value = {
            "users": [{"pk": 1, "username": "f1"}], "next_max_id": None
        }
        api._friendships.get_following.return_value = {
            "users": [{"pk": 2, "username": "c1", "follower_count": 500, "is_private": False, "full_name": "C", "is_verified": False}]
        }
        api._client.request.side_effect = [
            {"items": [{"caption": {"text": "#fashion"}}]},
            {"sections": [{"layout_content": {"medias": [
                {"media": {"user": {"pk": 3, "username": "c2", "follower_count": 800, "is_private": False, "full_name": "C2", "is_verified": True}}}
            ]}}]},
        ]
        result = api.find_lookalike("source", count=5, method="mixed")
        assert "users" in result
        assert result["count"] >= 1

    def test_overlap(self):
        api = self._make()
        api._users.get_by_username.side_effect = [{"pk": 1}, {"pk": 2}]
        api._friendships.get_followers.side_effect = [
            {"users": [{"username": "a1"}, {"username": "common"}], "next_max_id": None},
            {"users": [{"username": "b1"}, {"username": "common"}], "next_max_id": None},
        ]
        result = api.overlap("userA", "userB", max_followers=100)
        assert result["common_followers"] == 1
        assert result["overlap_rate"] > 0

    def test_insights(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._friendships.get_followers.return_value = {
            "users": [
                {"username": "f1", "is_verified": True, "is_private": False, "follower_count": 5000, "media_count": 20, "biography": "fashion model beauty"},
                {"username": "f2", "is_verified": False, "is_private": True, "follower_count": 200, "media_count": 5, "biography": "student"},
            ],
            "next_max_id": None,
        }
        result = api.insights("testuser", sample_size=5)
        assert result["sampled"] == 2
        assert "verified_rate" in result
        assert "engagement_potential" in result
        assert "audience_quality" in result

    def test_find_similar_accounts(self):
        api = self._make()
        api._users.get_by_username.return_value = {"pk": 123}
        api._client.request.return_value = {
            "users": [
                {"username": "sim1", "full_name": "Sim1", "follower_count": 5000, "is_verified": True, "biography": "test"},
                {"username": "sim2", "full_name": "Sim2", "follower_count": 3000, "is_verified": False, "biography": "bio"},
            ]
        }
        result = api.find_similar_accounts("test", count=2)
        assert len(result) == 2
        assert result[0]["username"] == "sim1"
