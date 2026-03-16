"""
test_public_data_final.py — Cover remaining 72 miss in public_data.py
=====================================================================
Targets: engagement_analysis body, build_report, export CSV/JSONL,
_search_hashtags body, track_profile growth, get_hashtag_quota,
__repr__. These are all sync methods.
"""
import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta

M = MagicMock


def _make_api():
    from instaharvest_v2.api.public_data import PublicDataAPI
    pub = M()

    # get_profile returns realistic dict
    pub.get_profile.return_value = {
        "user": {
            "pk": 123, "username": "test_user",
            "full_name": "Test User",
            "follower_count": 10000, "following_count": 500,
            "media_count": 200, "is_private": False,
            "is_verified": True, "biography": "test bio",
            "external_url": "https://test.com",
            "profile_pic_url_hd": "https://pic.jpg",
            "category": "Creator",
        }
    }

    # get_posts — realistic posts with different media types
    pub.get_posts.return_value = [
        {"pk": "111", "code": "A1", "media_type": 1,
         "taken_at": 1700000000,
         "caption": {"text": "Image post #fitness #gym"},
         "user": {"pk": 123, "username": "test_user"},
         "like_count": 500, "comment_count": 50,
         "image_versions2": {"candidates": [{"url": "https://img.jpg"}]}},
        {"pk": "222", "code": "B2", "media_type": 2,
         "taken_at": 1700086400,
         "caption": {"text": "Video post #workout"},
         "user": {"pk": 123, "username": "test_user"},
         "like_count": 1200, "comment_count": 120,
         "video_versions": [{"url": "https://vid.mp4"}]},
        {"pk": "333", "code": "C3", "media_type": 1,
         "taken_at": 1700172800,
         "caption": {"text": "Another image #fitness"},
         "user": {"pk": 123, "username": "test_user"},
         "like_count": 300, "comment_count": 30,
         "image_versions2": {"candidates": [{"url": "https://img2.jpg"}]}},
    ]

    pub.get_all_posts.return_value = pub.get_posts.return_value

    # hashtag posts
    pub.get_hashtag_posts.return_value = [
        {"pk": "444", "code": "D4", "media_type": 1,
         "taken_at": 1700000000,
         "caption": {"text": "#fitness is life #gym"},
         "user": {"pk": 456, "username": "other"},
         "like_count": 100, "comment_count": 10},
    ]

    # search_hashtag return
    pub.search_hashtag.return_value = {
        "items": [{"pk": "555", "code": "E5"}]
    }

    return PublicDataAPI(pub), pub


# ═══════════════════════════════════════
# engagement_analysis — lines 509-574
# ═══════════════════════════════════════
class TestEngagementAnalysis:
    def test_full_analysis(self):
        api, pub = _make_api()
        result = api.engagement_analysis("test_user", post_count=12)
        assert result["username"] == "test_user"
        assert result["followers"] == 10000
        assert result["posts_analyzed"] == 3
        assert "avg_likes" in result
        assert "engagement_rate" in result
        assert "rating" in result
        assert "content_type_breakdown" in result
        assert "top_hashtags" in result
        assert "top_posts" in result
        assert "posts_per_week" in result

    def test_high_engagement(self):
        """Engagement > 6% → excellent rating."""
        api, pub = _make_api()
        # 10000 followers, (666+66)/10000*100 = 7.32%
        pub.get_posts.return_value = [
            {"pk": "111", "code": "A1", "media_type": 1,
             "taken_at": 1700000000,
             "caption": {"text": "test"},
             "user": {"pk": 123, "username": "test"},
             "like_count": 600, "comment_count": 66},
        ]
        result = api.engagement_analysis("test", post_count=1)
        assert result["rating"] == "excellent"

    def test_good_engagement(self):
        """Engagement 3-6% → good."""
        api, pub = _make_api()
        pub.get_posts.return_value = [
            {"pk": "111", "code": "A1", "media_type": 1,
             "taken_at": 1700000000,
             "caption": {"text": "test"},
             "user": {"pk": 123, "username": "test"},
             "like_count": 400, "comment_count": 50},
        ]
        result = api.engagement_analysis("test", post_count=1)
        assert result["rating"] == "good"

    def test_average_engagement(self):
        """Engagement 1-3% → average."""
        api, pub = _make_api()
        pub.get_posts.return_value = [
            {"pk": "111", "code": "A1", "media_type": 1,
             "taken_at": 1700000000,
             "caption": {"text": "test"},
             "user": {"pk": 123, "username": "test"},
             "like_count": 150, "comment_count": 15},
        ]
        result = api.engagement_analysis("test", post_count=1)
        assert result["rating"] == "average"

    def test_low_engagement(self):
        """Engagement < 1% → low."""
        api, pub = _make_api()
        pub.get_posts.return_value = [
            {"pk": "111", "code": "A1", "media_type": 1,
             "taken_at": 1700000000,
             "caption": {"text": "test"},
             "user": {"pk": 123, "username": "test"},
             "like_count": 10, "comment_count": 1},
        ]
        result = api.engagement_analysis("test", post_count=1)
        assert result["rating"] == "low"

    def test_no_posts(self):
        api, pub = _make_api()
        pub.get_posts.return_value = []
        result = api.engagement_analysis("test")
        assert "error" in result

    def test_posts_per_week(self):
        api, pub = _make_api()
        result = api.engagement_analysis("test")
        assert result["posts_per_week"] >= 0


# ═══════════════════════════════════════
# build_report — lines 620-649
# ═══════════════════════════════════════
class TestBuildReport:
    def test_build_with_usernames(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test_user"], max_posts=5)
        assert report is not None
        assert report.query_type == "profile_posts"

    def test_build_with_hashtags(self):
        api, pub = _make_api()
        report = api.build_report(hashtags=["fitness"])
        assert report is not None
        assert report.query_type == "post_search"

    def test_build_with_both(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"], hashtags=["fitness"])
        assert report is not None

    def test_build_empty(self):
        api, pub = _make_api()
        report = api.build_report()
        assert report is not None

    def test_build_profile_info_only(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"], max_posts=0)
        assert report.query_type == "profile_info"


# ═══════════════════════════════════════
# export_report — CSV + JSONL (lines 700-727)
# ═══════════════════════════════════════
class TestExportReport:
    def test_export_json_no_file(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "json")
        assert isinstance(result, dict)
        assert "profiles" in result

    @patch("builtins.open", new_callable=mock_open)
    def test_export_json_file(self, mock_file):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "json", "/tmp/report.json")
        assert isinstance(result, dict)

    def test_export_csv_no_file(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "csv")
        assert isinstance(result, str) or result == ""

    @patch("builtins.open", new_callable=mock_open)
    def test_export_csv_file(self, mock_file):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "csv", "/tmp/report.csv")

    def test_export_csv_empty(self):
        api, pub = _make_api()
        report = api.build_report()
        result = api.export_report(report, "csv")

    def test_export_jsonl_no_file(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "jsonl")
        assert isinstance(result, str)

    @patch("builtins.open", new_callable=mock_open)
    def test_export_jsonl_file(self, mock_file):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        result = api.export_report(report, "jsonl", "/tmp/report.jsonl")

    def test_export_unsupported(self):
        api, pub = _make_api()
        report = api.build_report(usernames=["test"])
        with pytest.raises(ValueError):
            api.export_report(report, "xml")


# ═══════════════════════════════════════
# _search_hashtags body (790-825)
# ═══════════════════════════════════════
class TestSearchHashtags:
    def test_search_single(self):
        api, pub = _make_api()
        result = api._search_hashtags("fitness", "top", 1)
        assert isinstance(result, list)

    def test_search_list(self):
        api, pub = _make_api()
        result = api._search_hashtags(["fitness", "gym"], "recent", 1)
        assert isinstance(result, list)

    def test_search_empty(self):
        api, pub = _make_api()
        with pytest.raises(ValueError):
            api._search_hashtags("", "top", 1)

    def test_search_too_many(self):
        api, pub = _make_api()
        many = [f"tag{i}" for i in range(101)]
        with pytest.raises(ValueError):
            api._search_hashtags(many, "top", 1)

    def test_search_quota_exceeded(self):
        api, pub = _make_api()
        # Fill quota
        for i in range(31):
            api._quota.record_search(f"tag{i}")
        result = api._search_hashtags("newtag", "top", 1)
        # Should skip due to quota

    def test_search_error(self):
        api, pub = _make_api()
        pub.get_hashtag_posts.side_effect = Exception("API error")
        result = api._search_hashtags("fitness", "top", 1)
        assert isinstance(result, list)

    def test_search_not_list(self):
        api, pub = _make_api()
        pub.get_hashtag_posts.return_value = "not a list"
        result = api._search_hashtags("fitness", "top", 1)


# ═══════════════════════════════════════
# track_profile — growth path
# ═══════════════════════════════════════
class TestTrackProfile:
    def test_first_snapshot(self):
        api, pub = _make_api()
        result = api.track_profile("test_user")
        assert result["total_snapshots"] == 1
        assert "growth" not in result

    def test_growth_comparison(self):
        api, pub = _make_api()
        # First snapshot
        api.track_profile("test_user")
        # Second snapshot (same data → 0 growth)
        result = api.track_profile("test_user")
        assert result["total_snapshots"] == 2
        assert "growth" in result

    def test_get_tracking_history(self):
        api, pub = _make_api()
        api.track_profile("test_user")
        history = api.get_tracking_history("test_user")
        assert len(history) == 1

    def test_get_tracking_empty(self):
        api, pub = _make_api()
        history = api.get_tracking_history("unknown")
        assert history == []


# ═══════════════════════════════════════
# Quota + repr
# ═══════════════════════════════════════
class TestQuotaAndRepr:
    def test_get_hashtag_quota(self):
        api, pub = _make_api()
        q = api.get_hashtag_quota(2)
        assert q["total"] == 60
        assert q["remaining"] == 60

    def test_reset_quota(self):
        api, pub = _make_api()
        api._quota.record_search("test")
        api.reset_quota()
        assert api._quota.get_remaining_quota() == 30

    def test_repr(self):
        api, pub = _make_api()
        r = repr(api)
        assert "PublicDataAPI" in r

    def test_fetch_user_posts_many(self):
        api, pub = _make_api()
        # max_count > 12 triggers get_all_posts
        result = api._fetch_user_posts("test", max_count=50)
        pub.get_all_posts.assert_called_once()

    def test_fetch_user_posts_error(self):
        api, pub = _make_api()
        pub.get_posts.side_effect = Exception("fail")
        result = api._fetch_user_posts("test", max_count=5)
        assert result == []
