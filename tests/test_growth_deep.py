"""
test_growth_deep.py — Deep Coverage for GrowthAPI Method Bodies
================================================================
Covers GrowthLimits, GrowthFilters.matches(), and GrowthAPI internal
methods with proper MagicMock chains that exercise full method body.
~250 miss lines targeted.
"""
import pytest
import time
from unittest.mock import MagicMock, patch

M = MagicMock


# ═══════════════════════════════════════════════════════════
# GrowthLimits — all params
# ═══════════════════════════════════════════════════════════
class TestGrowthLimits:
    def test_defaults(self):
        from instaharvest_v2.api.growth import GrowthLimits
        gl = GrowthLimits()
        assert gl.max_per_hour == 20
        assert gl.max_per_day == 150
        assert gl.min_delay == 25.0
        assert gl.max_delay == 90.0
        assert gl.stop_on_challenge is True
        assert gl.stop_on_rate_limit is True

    def test_custom(self):
        from instaharvest_v2.api.growth import GrowthLimits
        gl = GrowthLimits(max_per_hour=5, max_per_day=30, min_delay=1.0, max_delay=2.0,
                          stop_on_challenge=False, stop_on_rate_limit=False)
        assert gl.max_per_hour == 5
        assert gl.stop_on_challenge is False


# ═══════════════════════════════════════════════════════════
# GrowthFilters — matches() all branches
# ═══════════════════════════════════════════════════════════
class TestGrowthFilters:
    def test_defaults(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters()
        assert gf.min_followers == 0
        assert gf.bio_keywords == []

    def test_matches_all_pass(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters()
        user = {"follower_count": 100, "media_count": 10, "biography": "test"}
        assert gf.matches(user) is True

    def test_min_followers_fail(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(min_followers=1000)
        assert gf.matches({"follower_count": 50, "media_count": 10}) is False

    def test_max_followers_fail(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(max_followers=100)
        assert gf.matches({"follower_count": 500, "media_count": 10}) is False

    def test_min_posts_fail(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(min_posts=5)
        assert gf.matches({"follower_count": 100, "media_count": 2}) is False

    def test_is_private_filter(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(is_private=False)
        assert gf.matches({"follower_count": 100, "media_count": 10, "is_private": True}) is False
        assert gf.matches({"follower_count": 100, "media_count": 10, "is_private": False}) is True

    def test_is_verified_filter(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(is_verified=True)
        assert gf.matches({"follower_count": 100, "media_count": 10, "is_verified": False}) is False

    def test_has_bio_filter(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(has_bio=True)
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": ""}) is False
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": "hello"}) is True

    def test_bio_keywords(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(bio_keywords=["fashion", "model"])
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": "I love fashion"}) is True
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": "tech nerd"}) is False

    def test_exclude_keywords(self):
        from instaharvest_v2.api.growth import GrowthFilters
        gf = GrowthFilters(exclude_keywords=["spam", "bot"])
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": "I am a bot"}) is False
        assert gf.matches({"follower_count": 100, "media_count": 10, "biography": "real person"}) is True


# ═══════════════════════════════════════════════════════════
# GrowthAPI — internal methods deep
# ═══════════════════════════════════════════════════════════
class TestGrowthAPIDeep:
    def _make(self):
        from instaharvest_v2.api.growth import GrowthAPI
        return GrowthAPI(M(), M(), M())

    def test_whitelist_blacklist(self):
        api = self._make()
        api.add_whitelist(["user1", "user2"])
        assert "user1" in api._whitelist
        api.add_blacklist(["spam1"])
        assert "spam1" in api._blacklist
        api.clear_whitelist()
        assert len(api._whitelist) == 0
        api.clear_blacklist()
        assert len(api._blacklist) == 0

    def test_action_log_property(self):
        api = self._make()
        assert api.action_log == []

    def test_log_action(self):
        api = self._make()
        api._log_action("follow", "testuser", 123)
        assert len(api._action_log) == 1
        assert api._action_log[0]["action"] == "follow"
        assert api._action_log[0]["username"] == "testuser"

    def test_log_action_overflow(self):
        api = self._make()
        for i in range(600):
            api._log_action("follow", f"user{i}", i)
        assert len(api._action_log) == 500

    def test_should_stop_rate_limit(self):
        from instaharvest_v2.api.growth import GrowthAPI, GrowthLimits
        limits = GrowthLimits(stop_on_rate_limit=True)
        # Create mock exception with specific class name
        class RateLimitError(Exception): pass
        assert GrowthAPI._should_stop(RateLimitError(), limits) is True

    def test_should_stop_challenge(self):
        from instaharvest_v2.api.growth import GrowthAPI, GrowthLimits
        limits = GrowthLimits(stop_on_challenge=True)
        class ChallengeRequired(Exception): pass
        assert GrowthAPI._should_stop(ChallengeRequired(), limits) is True

    def test_should_stop_login_required(self):
        from instaharvest_v2.api.growth import GrowthAPI, GrowthLimits
        limits = GrowthLimits()
        class LoginRequired(Exception): pass
        assert GrowthAPI._should_stop(LoginRequired(), limits) is True

    def test_should_not_stop(self):
        from instaharvest_v2.api.growth import GrowthAPI, GrowthLimits
        limits = GrowthLimits()
        assert GrowthAPI._should_stop(ValueError("test"), limits) is False

    @patch('time.sleep')
    def test_smart_delay(self, mock_sleep):
        from instaharvest_v2.api.growth import GrowthLimits
        api = self._make()
        limits = GrowthLimits(min_delay=0.001, max_delay=0.002)
        api._smart_delay(limits)
        mock_sleep.assert_called_once()

    def test_follow_users_of_body(self):
        """Test follow_users_of with mocked chain."""
        from instaharvest_v2.api.growth import GrowthAPI
        mock_users = M()
        mock_users.get_by_username.return_value = {"pk": 123, "username": "target"}
        mock_friends = M()
        mock_friends.get_followers.return_value = {
            "users": [{"pk": 1, "username": "u1", "follower_count": 100, "media_count": 10}],
            "next_max_id": None
        }
        mock_friends.follow.return_value = {"status": "ok"}
        api = GrowthAPI(M(), mock_users, mock_friends)
        with patch('time.sleep'):
            result = api.follow_users_of("target", count=1)
        assert result["followed"] == 1
        assert "u1" in result["users"]

    def test_follow_users_of_with_filters(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_users = M()
        mock_users.get_by_username.return_value = {"pk": 123}
        mock_friends = M()
        mock_friends.get_followers.return_value = {
            "users": [{"pk": 1, "username": "u1", "follower_count": 5, "media_count": 1}],
            "next_max_id": None
        }
        api = GrowthAPI(M(), mock_users, mock_friends)
        with patch('time.sleep'):
            result = api.follow_users_of("target", count=1, filters={"min_followers": 1000})
        assert result["followed"] == 0
        assert result["skipped"] >= 1

    def test_follow_users_of_blacklist(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_users = M()
        mock_users.get_by_username.return_value = {"pk": 123}
        mock_friends = M()
        mock_friends.get_followers.return_value = {
            "users": [{"pk": 1, "username": "blocked_user"}],
            "next_max_id": None
        }
        api = GrowthAPI(M(), mock_users, mock_friends)
        api.add_blacklist(["blocked_user"])
        with patch('time.sleep'):
            result = api.follow_users_of("target", count=1)
        assert result["followed"] == 0
        assert result["skipped"] >= 1

    def test_unfollow_non_followers_body(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_client = M()
        sm = M()
        sess = M()
        sess.ds_user_id = "999"
        sm.get_session.return_value = sess
        mock_client._session_mgr = sm
        mock_friends = M()
        # Followers: user1
        # Following: user1, user2 (user2 is non-follower)
        mock_friends.get_followers.return_value = {"users": [{"pk": 1, "username": "user1"}], "next_max_id": None}
        mock_friends.get_following.return_value = {"users": [{"pk": 1, "username": "user1"}, {"pk": 2, "username": "user2"}], "next_max_id": None}
        mock_friends.unfollow.return_value = {"status": "ok"}
        api = GrowthAPI(mock_client, M(), mock_friends)
        with patch('time.sleep'):
            result = api.unfollow_non_followers(max_count=1)
        assert result["unfollowed"] == 1

    def test_get_fans(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_client = M()
        sm = M()
        sess = M()
        sess.ds_user_id = "999"
        sm.get_session.return_value = sess
        mock_client._session_mgr = sm
        mock_friends = M()
        mock_friends.get_followers.return_value = {"users": [{"pk": 1, "username": "fan1"}, {"pk": 2, "username": "mutual"}], "next_max_id": None}
        mock_friends.get_following.return_value = {"users": [{"pk": 2, "username": "mutual"}], "next_max_id": None}
        api = GrowthAPI(mock_client, M(), mock_friends)
        fans = api.get_fans()
        assert len(fans) == 1
        assert fans[0]["username"] == "fan1"

    def test_follow_hashtag_users_body(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_client = M()
        mock_client.request.return_value = {
            "sections": [{"layout_content": {"medias": [
                {"media": {"user": {"pk": 1, "username": "u1", "follower_count": 100, "media_count": 5}}}
            ]}}]
        }
        mock_friends = M()
        mock_friends.follow.return_value = {"status": "ok"}
        api = GrowthAPI(mock_client, M(), mock_friends)
        with patch('time.sleep'):
            result = api.follow_hashtag_users("fashion", count=1)
        assert result["followed"] == 1

    def test_on_progress_callback(self):
        from instaharvest_v2.api.growth import GrowthAPI
        mock_users = M()
        mock_users.get_by_username.return_value = {"pk": 123}
        mock_friends = M()
        mock_friends.get_followers.return_value = {
            "users": [{"pk": 1, "username": "u1", "follower_count": 100, "media_count": 10}],
            "next_max_id": None}
        mock_friends.follow.return_value = {"status": "ok"}
        api = GrowthAPI(M(), mock_users, mock_friends)
        progress_calls = []
        with patch('time.sleep'):
            result = api.follow_users_of("target", count=1, on_progress=lambda f,t,u: progress_calls.append((f,t,u)))
        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1, "u1")
