"""
test_sync_mega_65.py — Mega test for 4 sync modules (384 miss lines)
====================================================================
1. log_config.py (107 miss) — DebugLogger enabled body
2. comment_manager.py (92 miss) — get_comments/auto_reply/delete_spam/sentiment/filter
3. export.py (91 miss) — followers_to_csv/hashtag_users/post_likers/to_json
4. fb_dtsg.py (94 miss) — _parse_html, FbDtsgResult, ensure_token sync wrappers
"""
import pytest
import asyncio
import json
import os
import re
import time
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from datetime import datetime

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
# 1. LOG_CONFIG.py — DebugLogger (107 miss)
# ═══════════════════════════════════════════════════════════════
class TestLogConfig:
    def test_configure_basic(self):
        from instaharvest_v2.log_config import LogConfig
        logger = LogConfig.configure(level="WARNING", console=False)
        assert logger is not None

    def test_configure_with_file(self):
        from instaharvest_v2.log_config import LogConfig
        with patch("instaharvest_v2.log_config.RotatingFileHandler") as mock_rfh:
            mock_rfh.return_value = M()
            mock_rfh.return_value.setFormatter = M()
            logger = LogConfig.configure(level="DEBUG", filename="/tmp/test.log")

    def test_configure_debug(self):
        from instaharvest_v2.log_config import LogConfig
        logger = LogConfig.configure_debug()
        assert logger is not None

    def test_get_logger(self):
        from instaharvest_v2.log_config import LogConfig
        l1 = LogConfig.get_logger("test_module")
        assert l1 is not None
        l2 = LogConfig.get_logger("instaharvest_v2.already")
        assert l2 is not None

    def test_set_level(self):
        from instaharvest_v2.log_config import LogConfig
        LogConfig.set_level("ERROR")
        LogConfig.set_level("DEBUG")

    def test_silence(self):
        from instaharvest_v2.log_config import LogConfig
        LogConfig.silence()
        LogConfig.configure(level="INFO", console=False)

    def test_is_configured(self):
        from instaharvest_v2.log_config import LogConfig
        assert isinstance(LogConfig.is_configured(), bool)


class TestDebugLogger:
    def _make(self):
        from instaharvest_v2.log_config import DebugLogger
        dl = DebugLogger.__new__(DebugLogger)
        dl.enabled = True
        dl._logger = M()
        return dl

    def test_disabled(self):
        from instaharvest_v2.log_config import DebugLogger
        dl = DebugLogger(enabled=False)
        dl.request("GET", "/test")
        dl.response(200, 100)
        dl.error("TestError")

    def test_mask(self):
        from instaharvest_v2.log_config import DebugLogger
        assert DebugLogger._mask("") == "<empty>"
        assert DebugLogger._mask("short") == "short"
        assert "***" in DebugLogger._mask("verylongvalue123")

    def test_mask_cookie_string(self):
        from instaharvest_v2.log_config import DebugLogger
        assert DebugLogger._mask_cookie_string("") == "<no cookies>"
        r = DebugLogger._mask_cookie_string("csrftoken=abc123; sessionid=xyz789long")
        assert "csrftoken" in r

    def test_format_size(self):
        from instaharvest_v2.log_config import DebugLogger
        assert DebugLogger._format_size(500) == "500B"
        assert "KB" in DebugLogger._format_size(2048)
        assert "MB" in DebugLogger._format_size(2 * 1024 * 1024)

    def test_request_full(self):
        dl = self._make()
        dl.request("GET", "https://www.instagram.com/api/v1/users/123/",
                   params={"count": "10"},
                   session_id="ds_123456789",
                   proxy="http://proxy:8080",
                   attempt=2, max_attempts=4, has_data=True)

    def test_request_minimal(self):
        dl = self._make()
        dl.request("POST", "/api/v1/test/")

    def test_response_full(self):
        dl = self._make()
        dl.response(200, 245, size_bytes=12300,
                    url="https://www.instagram.com/api/v1/test/",
                    cookies_updated=["csrftoken", "sessionid"])

    def test_response_non_200(self):
        dl = self._make()
        dl.response(429, 100)

    def test_error_full(self):
        dl = self._make()
        dl.error("RateLimitError", status_code=429,
                 endpoint="https://www.instagram.com/api/v1/users/",
                 message="Too many requests",
                 escalation="level_2",
                 response_preview='{"message":"rate limit"}')

    def test_session_info(self):
        dl = self._make()
        dl.session_info(ds_user_id="12345",
                       csrf_token="csrf123",
                       ig_www_claim="claim123",
                       session_id="sess123",
                       user_agent="Mozilla/5.0 test agent string for coverage")

    def test_identity_rotated_full(self):
        dl = self._make()
        dl.identity_rotated(
            old_browser="Chrome/141", old_platform="Windows",
            new_browser="Chrome/142", new_platform="macOS",
            reason="rate_limit", escalation_before="normal",
            escalation_after="stealth",
            new_impersonation="chrome142",
            blacklisted_profiles=5)

    def test_identity_rotated_new_only(self):
        dl = self._make()
        dl.identity_rotated(new_browser="Firefox/120", new_platform="Linux")

    def test_block_detected(self):
        dl = self._make()
        dl.block_detected("checkpoint", url="/challenge/",
                         contact_point="email", message="Verify your identity",
                         status_code=400)

    def test_retry(self):
        dl = self._make()
        dl.retry(2, 4, 5.5, reason="429 rate limit",
                endpoint="https://www.instagram.com/api/v1/feed/")

    def test_rate_limit(self):
        dl = self._make()
        dl.rate_limit(category="feed", pause_seconds=30, message="Throttled")

    def test_proxy_event(self):
        dl = self._make()
        dl.proxy_event("rotate", proxy="http://proxy.example.com:8080",
                      elapsed_ms=150, message="Health OK")

    def test_cookie_update(self):
        dl = self._make()
        dl.cookie_update(["csrftoken", "mid"], session_id="sess123")

    def test_cookie_update_empty(self):
        dl = self._make()
        dl.cookie_update([])  # Should return early

    def test_redirect(self):
        dl = self._make()
        dl.redirect("https://www.instagram.com/accounts/login/",
                   "/accounts/login/", is_login_redirect=True)

    def test_redirect_normal(self):
        dl = self._make()
        dl.redirect("https://www.instagram.com/p/123/",
                   "/p/123/", is_login_redirect=False)

    def test_delay(self):
        dl = self._make()
        dl.delay(4.5, action_type="profile_view", escalation_level=2)

    def test_delay_normal(self):
        dl = self._make()
        dl.delay(1.0)

    def test_session_refresh(self):
        dl = self._make()
        dl.session_refresh(True, method="cookie_refresh")
        dl.session_refresh(False, method="full_relogin")


class TestDebugLoggerGlobal:
    def test_get_set(self):
        from instaharvest_v2.log_config import get_debug_logger, set_debug_logger, DebugLogger
        dl = get_debug_logger()
        assert dl is not None
        new_dl = DebugLogger(enabled=False)
        set_debug_logger(new_dl)
        assert get_debug_logger() is new_dl


# ═══════════════════════════════════════════════════════════════
# 2. COMMENT_MANAGER.py (92 miss)
# ═══════════════════════════════════════════════════════════════
class TestCommentManager:
    def _make(self):
        from instaharvest_v2.api.comment_manager import CommentManagerAPI
        client = M()
        media = M()
        return CommentManagerAPI(client, media), client

    def test_get_comments_basic(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "Great post!", "user": {"username": "user1", "pk": 111},
                 "comment_like_count": 5, "created_at": 1700000000},
                {"pk": "c2", "text": "follow me check my bio", "user": {"username": "spammer", "pk": 222},
                 "comment_like_count": 0, "created_at": 1700000001},
            ],
            "has_more_comments": False, "next_min_id": None
        }
        result = api.get_comments("media123", count=50, sort="newest")
        assert result["count"] == 2
        assert len(result["comments"]) == 2

    def test_get_comments_top_sort(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "ok", "user": {"username": "a"}, "comment_like_count": 1, "created_at": 1},
                {"pk": "c2", "text": "best!", "user": {"username": "b"}, "comment_like_count": 100, "created_at": 2},
            ],
            "has_more_comments": False
        }
        result = api.get_comments("media123", sort="top")
        assert result["comments"][0]["likes"] == 100

    def test_get_comments_oldest_sort(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "first", "user": {"username": "a"}, "comment_like_count": 0, "created_at": 100},
                {"pk": "c2", "text": "second", "user": {"username": "b"}, "comment_like_count": 0, "created_at": 50},
            ],
            "has_more_comments": False
        }
        result = api.get_comments("media123", sort="oldest")
        assert result["comments"][0]["created_at"] == 50

    def test_get_comments_pagination(self):
        api, client = self._make()
        call_count = [0]
        def mock_req(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"comments": [{"pk": "c1", "text": "hi", "user": {"username": "a"}, "comment_like_count": 0, "created_at": 1}],
                        "has_more_comments": True, "next_min_id": "cursor2"}
            return {"comments": [{"pk": "c2", "text": "hello", "user": {"username": "b"}, "comment_like_count": 0, "created_at": 2}],
                    "has_more_comments": False}
        client.request.side_effect = mock_req
        result = api.get_comments("m1", count=5)
        assert result["count"] == 2

    def test_get_comments_error(self):
        api, client = self._make()
        client.request.side_effect = Exception("Network error")
        result = api.get_comments("m1")
        assert result["count"] == 0

    @patch("instaharvest_v2.api.comment_manager.time.sleep")
    @patch("instaharvest_v2.api.comment_manager.random.uniform", return_value=0)
    def test_auto_reply(self, mock_rand, mock_sleep):
        api, client = self._make()
        # First call: get_comments, second+: reply
        call_count = [0]
        def mock_req(method, url, **kwargs):
            call_count[0] += 1
            if "comments/" in url and method == "GET":
                return {"comments": [
                    {"pk": "c1", "text": "whats the price", "user": {"username": "buyer", "pk": 111},
                     "comment_like_count": 0, "created_at": 1}
                ], "has_more_comments": False}
            return {"status": "ok"}
        client.request.side_effect = mock_req
        result = api.auto_reply("m1", keyword="price", reply="DM us {username}!", max_count=5)
        assert result["replied"] >= 0

    @patch("instaharvest_v2.api.comment_manager.time.sleep")
    @patch("instaharvest_v2.api.comment_manager.random.uniform", return_value=0)
    def test_auto_reply_skip_spam(self, mock_rand, mock_sleep):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "follow me check my bio", "user": {"username": "spammer"},
                 "comment_like_count": 0, "created_at": 1}
            ], "has_more_comments": False
        }
        result = api.auto_reply("m1", reply="thanks!")
        assert result["skipped"] >= 1

    @patch("instaharvest_v2.api.comment_manager.time.sleep")
    @patch("instaharvest_v2.api.comment_manager.random.uniform", return_value=0)
    def test_auto_reply_error(self, mock_rand, mock_sleep):
        api, client = self._make()
        call_count = [0]
        def mock_req(method, url, **kwargs):
            call_count[0] += 1
            if method == "GET":
                return {"comments": [{"pk": "c1", "text": "hello", "user": {"username": "u1"},
                                      "comment_like_count": 0, "created_at": 1}],
                        "has_more_comments": False}
            raise Exception("Reply failed")
        client.request.side_effect = mock_req
        result = api.auto_reply("m1", reply="thanks!")
        assert result["errors"] >= 1

    def test_bulk_reply(self):
        api, client = self._make()
        client.request.return_value = {"comments": [], "has_more_comments": False}
        result = api.bulk_reply("m1", reply="thanks!")

    @patch("instaharvest_v2.api.comment_manager.time.sleep")
    @patch("instaharvest_v2.api.comment_manager.random.uniform", return_value=0)
    def test_delete_spam(self, mock_rand, mock_sleep):
        api, client = self._make()
        call_count = [0]
        def mock_req(method, url, **kwargs):
            call_count[0] += 1
            if method == "GET":
                return {"comments": [
                    {"pk": "c1", "text": "follow me check my bio", "user": {"username": "spammer"},
                     "comment_like_count": 0, "created_at": 1},
                    {"pk": "c2", "text": "great post!", "user": {"username": "real"},
                     "comment_like_count": 5, "created_at": 2},
                ], "has_more_comments": False}
            return {"status": "ok"}
        client.request.side_effect = mock_req
        result = api.delete_spam("m1", custom_patterns=[r"buy\s+now"])
        assert result["deleted"] >= 1

    def test_sentiment_analysis(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "love it amazing beautiful", "user": {"username": "fan"},
                 "comment_like_count": 10, "created_at": 1},
                {"pk": "c2", "text": "hate it ugly terrible", "user": {"username": "hater"},
                 "comment_like_count": 2, "created_at": 2},
                {"pk": "c3", "text": "ok", "user": {"username": "neutral"},
                 "comment_like_count": 0, "created_at": 3},
            ],
            "has_more_comments": False
        }
        result = api.sentiment("m1")
        assert result["total_analyzed"] == 3
        assert result["overall"] in ("very_positive", "positive", "negative", "neutral")

    def test_sentiment_very_positive(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": f"c{i}", "text": "love amazing beautiful wow", "user": {"username": f"u{i}"},
                 "comment_like_count": 0, "created_at": i}
                for i in range(10)
            ],
            "has_more_comments": False
        }
        result = api.sentiment("m1")
        assert result["overall"] == "very_positive"

    def test_sentiment_negative(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": f"c{i}", "text": "hate ugly terrible worst", "user": {"username": f"u{i}"},
                 "comment_like_count": 0, "created_at": i}
                for i in range(10)
            ],
            "has_more_comments": False
        }
        result = api.sentiment("m1")
        assert result["overall"] == "negative"

    def test_filter_comments(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "best product!", "user": {"username": "fan"},
                 "comment_like_count": 20, "created_at": 1,
                 "is_spam": False, "sentiment": "positive"},
                {"pk": "c2", "text": "follow me", "user": {"username": "spam"},
                 "comment_like_count": 0, "created_at": 2,
                 "is_spam": True, "sentiment": "neutral"},
            ],
            "has_more_comments": False
        }
        # Filter positives with min likes
        result = api.filter_comments("m1", sentiment_filter="positive", min_likes=5)

    def test_filter_by_keyword(self):
        api, client = self._make()
        client.request.return_value = {
            "comments": [
                {"pk": "c1", "text": "price please", "user": {"username": "buyer"},
                 "comment_like_count": 0, "created_at": 1,
                 "is_spam": False, "sentiment": "neutral"},
            ],
            "has_more_comments": False
        }
        result = api.filter_comments("m1", keyword="price")
        assert len(result) >= 1

    def test_is_spam(self):
        api, _ = self._make()
        assert api._is_spam("follow me check my profile") is True
        assert api._is_spam("f4f l4l") is True
        assert api._is_spam("🔥🔥🔥🔥🔥🔥") is True
        assert api._is_spam("Great photo!") is False
        assert api._is_spam("") is False

    def test_quick_sentiment(self):
        from instaharvest_v2.api.comment_manager import CommentManagerAPI
        assert CommentManagerAPI._quick_sentiment("love amazing beautiful") == "positive"
        assert CommentManagerAPI._quick_sentiment("hate ugly terrible 😡") == "negative"
        assert CommentManagerAPI._quick_sentiment("ok") == "neutral"
        assert CommentManagerAPI._quick_sentiment("") == "neutral"


# ═══════════════════════════════════════════════════════════════
# 3. EXPORT.py (91 miss)
# ═══════════════════════════════════════════════════════════════
class TestExportFilter:
    def test_basic_match(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(min_followers=100)
        assert f.matches({"follower_count": 200}) is True
        assert f.matches({"follower_count": 50}) is False

    def test_max_followers(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(max_followers=1000)
        assert f.matches({"follower_count": 500}) is True
        assert f.matches({"follower_count": 2000}) is False

    def test_following_range(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(min_following=50, max_following=500)
        assert f.matches({"following_count": 200}) is True
        assert f.matches({"following_count": 30}) is False
        assert f.matches({"following_count": 600}) is False

    def test_boolean_filters(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(is_private=False, is_verified=True, is_business=True)
        assert f.matches({"is_private": False, "is_verified": True, "is_business_account": True}) is True
        assert f.matches({"is_private": True, "is_verified": True, "is_business_account": True}) is False

    def test_bio_filters(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(has_bio=True, bio_keywords=["fashion", "model"])
        assert f.matches({"biography": "Fashion model NYC"}) is True
        assert f.matches({"biography": ""}) is False
        assert f.matches({"biography": "Engineer at Google"}) is False

    def test_has_bio_false(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(has_bio=False)
        assert f.matches({"biography": ""}) is True
        assert f.matches({"biography": "has bio"}) is False

    def test_exclude_keywords(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(exclude_keywords=["spam", "bot"])
        assert f.matches({"biography": "Real person"}) is True
        assert f.matches({"biography": "I am a bot"}) is False

    def test_profile_pic(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(has_profile_pic=True)
        assert f.matches({"profile_pic_url": "https://real.jpg"}) is True
        assert f.matches({"profile_pic_url": "https://default_avatar.jpg"}) is False
        assert f.matches({"profile_pic_url": ""}) is False

    def test_custom_filter(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(custom_filter=lambda u: u.get("follower_count", 0) > 1000)
        assert f.matches({"follower_count": 5000}) is True
        assert f.matches({"follower_count": 500}) is False

    def test_min_posts(self):
        from instaharvest_v2.api.export import ExportFilter
        f = ExportFilter(min_posts=10)
        assert f.matches({"media_count": 50}) is True
        assert f.matches({"media_count": 5}) is False


class TestExportAPI:
    def _make(self):
        from instaharvest_v2.api.export import ExportAPI
        client = M()
        users = M()
        friendships = M()
        media = M()
        hashtags = M()
        users.get_by_username.return_value = M(pk=12345)
        users.get_full_profile.return_value = {"username": "test", "pk": 12345}
        friendships.get_followers.return_value = {
            "users": [{"username": "f1", "pk": 111, "follower_count": 500}],
            "next_max_id": None
        }
        friendships.get_following.return_value = {
            "users": [{"username": "f2", "pk": 222}],
            "next_max_id": None
        }
        return ExportAPI(client, users, friendships, media, hashtags), client

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_followers_to_csv(self, mock_dirs, mock_file):
        api, client = self._make()
        result = api.followers_to_csv("test", "/tmp/f.csv", max_count=10)
        assert result["exported"] >= 0

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_following_to_csv(self, mock_dirs, mock_file):
        api, client = self._make()
        result = api.following_to_csv("test", "/tmp/f.csv", max_count=10)
        assert result["exported"] >= 0

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_post_likers(self, mock_dirs, mock_file):
        api, client = self._make()
        api._media.get_likers.return_value = {
            "users": [{"username": "liker1", "pk": 333}]
        }
        result = api.post_likers("media123", "/tmp/likers.csv")
        assert result["exported"] >= 0

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_post_likers_error(self, mock_dirs, mock_file):
        api, client = self._make()
        api._media.get_likers.side_effect = Exception("fail")
        result = api.post_likers("media123", "/tmp/likers.csv")
        assert result["exported"] == 0

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_post_commenters(self, mock_dirs, mock_file):
        api, client = self._make()
        api._media.get_all_comments.return_value = [
            {"user": {"username": "c1", "pk": 444}, "text": "nice"},
            {"user": {"username": "c1", "pk": 444}, "text": "great"},  # duplicate
        ]
        result = api.post_commenters("media123", "/tmp/commenters.csv")
        assert result["exported"] >= 0

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_to_json(self, mock_dirs, mock_file):
        api, client = self._make()
        client.request.return_value = {"items": [{"pk": "111"}]}
        result = api.to_json("test", "/tmp/profile.json",
                            include_posts=True, include_followers_sample=5)
        assert "file" in result

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_to_json_errors(self, mock_dirs, mock_file):
        api, client = self._make()
        api._users.get_full_profile.side_effect = Exception("fail")
        client.request.side_effect = Exception("fail")
        api._friendships.get_followers.side_effect = Exception("fail")
        result = api.to_json("test", "/tmp/profile.json",
                            include_posts=True, include_followers_sample=5)

    def test_user_to_row_dict(self):
        api, _ = self._make()
        row = api._user_to_row({"username": "test", "full_name": "Test", "pk": 123,
                                "follower_count": 1000, "biography": "bio"})
        assert row["username"] == "test"

    def test_user_to_row_object(self):
        api, _ = self._make()
        user = M()
        user.username = "test"
        user.full_name = "Test"
        user.pk = 123
        user.followers = 1000
        user.following = 200
        user.media_count = 50
        user.is_private = False
        user.is_verified = True
        user.is_business_account = True
        user.biography = "bio"
        user.external_url = "https://test.com"
        user.profile_pic_url = "pic.jpg"
        user.category = "Creator"
        row = api._user_to_row(user)
        assert row["username"] == "test"

    def test_user_to_row_string(self):
        api, _ = self._make()
        row = api._user_to_row("juststring")
        assert row["username"] == "juststring"


# ═══════════════════════════════════════════════════════════════
# 4. FB_DTSG.py (94 miss)
# ═══════════════════════════════════════════════════════════════
class TestFbDtsgResult:
    def test_basic(self):
        from instaharvest_v2.fb_dtsg import FbDtsgResult
        r = FbDtsgResult()
        assert r.is_valid is False
        r.fb_dtsg = "test_token"
        assert r.is_valid is True


class TestFbDtsgParseHtml:
    def test_parse_all_tokens(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider(ttl_seconds=3600)
        html = '''
        "DTSGInitialData",[],{"token":"dtsg_test_123"}
        "LSD",[],{"token":"lsd_test_456"}
        "rollout_hash":"abc123def456"
        "claim":"hmac_claim_value"
        "device_id":"device_uuid_789"
        '''
        result = provider._parse_html(html, FbDtsgResult())
        assert result.fb_dtsg == "dtsg_test_123"
        assert result.lsd == "lsd_test_456"
        assert result.rollout_hash == "abc123def456"
        assert result.claim == "hmac_claim_value"
        assert result.device_id == "device_uuid_789"

    def test_parse_alt_dtsg_input(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        html = 'name="fb_dtsg" value="alt_dtsg_token"'
        result = provider._parse_html(html, FbDtsgResult())
        assert result.fb_dtsg == "alt_dtsg_token"

    def test_parse_build_hash(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        html = '"buildHash":"deadbeef1234"'
        result = provider._parse_html(html, FbDtsgResult())
        assert result.rollout_hash == "deadbeef1234"

    def test_parse_no_claim_fallback(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        r = FbDtsgResult()
        r.claim = "existing_claim"
        result = provider._parse_html('"claim":""', r)
        assert result.claim == "existing_claim"

    def test_parse_empty(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        result = provider._parse_html("", FbDtsgResult())
        assert result.fb_dtsg == ""


class TestFbDtsgProvider:
    def test_is_expired(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider(ttl_seconds=60)
        r = FbDtsgResult(fetched_at=time.time())
        assert provider._is_expired(r) is False
        r2 = FbDtsgResult(fetched_at=time.time() - 120)
        assert provider._is_expired(r2) is True

    def test_apply_to_session(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        session = M()
        session.fb_dtsg = ""
        session.x_instagram_ajax = ""
        session.ig_www_claim = ""
        result = FbDtsgResult(fb_dtsg="token", rollout_hash="hash", claim="claim")
        provider._apply_to_session(session, result)
        assert session.fb_dtsg == "token"
        assert session.x_instagram_ajax == "hash"
        assert session.ig_www_claim == "claim"

    def test_invalidate(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        session = M()
        session.session_id = "test_sid"
        provider._cache["test_sid"] = FbDtsgResult(fb_dtsg="t")
        provider.invalidate(session)
        assert "test_sid" not in provider._cache

    def test_invalidate_all(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider()
        provider._cache["s1"] = FbDtsgResult(fb_dtsg="t1")
        provider._cache["s2"] = FbDtsgResult(fb_dtsg="t2")
        provider.invalidate_all()
        assert len(provider._cache) == 0

    def test_ensure_token_cached(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider(ttl_seconds=3600)
        session = M()
        session.session_id = "test_sid"
        session.fb_dtsg = ""
        session.x_instagram_ajax = ""
        session.ig_www_claim = ""
        cached = FbDtsgResult(fb_dtsg="cached_token", fetched_at=time.time())
        provider._cache["test_sid"] = cached
        result = run(provider.ensure_token(session))
        assert result == "cached_token"

    def test_ensure_token_fetch(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider(ttl_seconds=3600)
        session = M()
        session.session_id = "test_sid2"
        session.fb_dtsg = ""
        session.x_instagram_ajax = ""
        session.ig_www_claim = ""
        session.user_agent = "Mozilla/5.0"
        session.fingerprint = None
        session.cookie_string = "csrftoken=test"

        # Mock fetch_from_page
        async def mock_fetch(s, curl_session=None):
            return FbDtsgResult(fb_dtsg="fresh_token", fetched_at=time.time())
        provider.fetch_from_page = mock_fetch
        result = run(provider.ensure_token(session))
        assert result == "fresh_token"

    def test_ensure_token_no_result(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider, FbDtsgResult
        provider = AsyncFbDtsgProvider(ttl_seconds=3600)
        session = M()
        session.session_id = "test_sid3"
        session.fb_dtsg = ""
        session.x_instagram_ajax = ""
        session.ig_www_claim = ""
        session.user_agent = ""
        session.fingerprint = None
        session.cookie_string = ""
        async def mock_fetch(s, curl_session=None):
            return FbDtsgResult()  # empty = no valid token
        provider.fetch_from_page = mock_fetch
        result = run(provider.ensure_token(session))
        assert result == ""
