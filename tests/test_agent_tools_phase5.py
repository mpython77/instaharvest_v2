"""
test_agent_tools_phase5.py
==========================
Comprehensive tests for Phase 5 agent tools (47 tools).
Tests: auth, analytics, insights, audience, ab_test,
       automation, scheduler, monitor, pipeline, bulk_download,
       ai_suggest, comment_manager.

Uses MagicMock for ig instance — no real Instagram calls.
"""

import json
import pytest
from unittest.mock import MagicMock, PropertyMock

# ─── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def mock_ig():
    """Create a fully mocked Instagram instance with all sub-modules."""
    ig = MagicMock()

    # Auth
    ig.auth.login.return_value = {"user_id": "12345", "status": "ok"}
    ig.auth.validate_session.return_value = True
    ig.auth.logout.return_value = {"status": "ok"}

    # Analytics
    ig.analytics.engagement_rate.return_value = {"rate": 3.5, "avg_likes": 150, "avg_comments": 12}
    ig.analytics.best_posting_times.return_value = {"best_hours": [9, 12, 18], "best_days": ["Mon", "Wed"]}
    ig.analytics.content_analysis.return_value = {"photo": 60, "video": 25, "carousel": 15}
    ig.analytics.profile_summary.return_value = {"followers": 10000, "engagement": 3.5}
    ig.analytics.compare.return_value = [
        {"username": "user1", "followers": 5000},
        {"username": "user2", "followers": 8000},
    ]

    # Insights
    ig.insights.get_account_summary.return_value = {"reach": 5000, "impressions": 12000}
    ig.insights.get_media_insights.return_value = {"reach": 800, "saves": 25, "shares": 10}
    ig.insights.get_business_info.return_value = {"category": "Fashion", "contact": "email@test.com"}
    ig.insights.get_ads_accounts.return_value = [{"id": "act_123", "name": "My Ads"}]

    # Audience
    ig.audience.find_lookalike.return_value = [{"username": "similar_1"}, {"username": "similar_2"}]
    ig.audience.overlap.return_value = {"overlap_count": 150, "overlap_pct": 12.5}
    ig.audience.insights.return_value = {"top_country": "US", "top_city": "New York"}

    # A/B Test
    ig.ab_test.create.return_value = {"test_id": "test_001", "status": "created"}
    ig.ab_test.run.return_value = {"test_id": "test_001", "status": "running"}
    ig.ab_test.results.return_value = {"winner": "variant_a", "confidence": 95.2}
    ig.ab_test.list_tests.return_value = [{"test_id": "test_001", "status": "done"}]

    # Automation
    ig.automation.dm_new_followers.return_value = {"sent": 5, "failed": 0}
    ig.automation.comment_on_hashtag.return_value = {"commented": 3, "skipped": 2}
    ig.automation.auto_like_feed.return_value = {"liked": 8}
    ig.automation.auto_like_hashtag.return_value = {"liked": 6}
    ig.automation.watch_stories.return_value = {"watched": 15}
    ig.automation.action_log.return_value = [{"action": "like", "time": "10:30"}]

    # Scheduler
    ig.scheduler.post_at.return_value = {"job_id": "job_001", "scheduled_for": "2024-01-15 10:00"}
    ig.scheduler.story_at.return_value = {"job_id": "job_002", "scheduled_for": "2024-01-15 12:00"}
    ig.scheduler.reel_at.return_value = {"job_id": "job_003", "scheduled_for": "2024-01-15 14:00"}
    ig.scheduler.list_jobs.return_value = [{"job_id": "job_001", "status": "pending"}]
    ig.scheduler.cancel.return_value = {"status": "cancelled", "job_id": "job_001"}

    # Monitor
    ig.monitor.watch.return_value = {"status": "watching", "username": "target"}
    ig.monitor.unwatch.return_value = {"status": "unwatched", "username": "target"}
    ig.monitor.check_now.return_value = {"checked": 3, "changes": 1}
    ig.monitor.event_log.return_value = [{"event": "new_post", "username": "target"}]
    ig.monitor.get_stats.return_value = {"watched": 5, "total_events": 42}

    # Pipeline
    ig.pipeline.to_sqlite.return_value = {"status": "ok", "rows": 150, "db_path": "pipeline.db"}
    ig.pipeline.to_jsonl.return_value = {"status": "ok", "lines": 150, "path": "pipeline.jsonl"}

    # Bulk Download
    ig.bulk_download.all_posts.return_value = {"downloaded": 50, "failed": 2}
    ig.bulk_download.all_stories.return_value = {"downloaded": 8}
    ig.bulk_download.all_highlights.return_value = {"downloaded": 12}
    ig.bulk_download.everything.return_value = {"posts": 50, "stories": 8, "highlights": 12}

    # AI Suggest
    ig.ai_suggest.hashtags_from_caption.return_value = ["#fashion", "#style", "#ootd"]
    ig.ai_suggest.caption_ideas.return_value = ["Caption idea 1", "Caption idea 2"]

    # Comment Manager
    ig.comment_manager.get_comments.return_value = [{"user": "fan1", "text": "Great!"}]
    ig.comment_manager.auto_reply.return_value = {"replied": 5, "skipped": 3}
    ig.comment_manager.delete_spam.return_value = {"deleted": 3}
    ig.comment_manager.sentiment.return_value = {"positive": 70, "negative": 10, "neutral": 20}

    return ig


# ═══════════════════════════════════════════════════════════
# AUTH TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestAuthTools:
    def test_login_success(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_login
        result = json.loads(handle_login(
            {"username": "testuser", "password": "testpass"}, ig=mock_ig
        ))
        assert result["status"] == "ok"
        assert "testuser" in result["message"]
        mock_ig.auth.login.assert_called_once()

    def test_login_missing_creds(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_login
        result = json.loads(handle_login({"username": ""}, ig=mock_ig))
        assert "error" in result

    def test_login_no_ig(self):
        from instaharvest_v2.agent.tools.auth_tools import handle_login
        result = json.loads(handle_login({"username": "x", "password": "y"}, ig=None))
        assert "error" in result

    def test_validate_session(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_validate_session
        result = json.loads(handle_validate_session({}, ig=mock_ig, is_logged_in=True))
        assert result["valid"] is True

    def test_validate_session_not_logged_in(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_validate_session
        result = json.loads(handle_validate_session({}, ig=mock_ig, is_logged_in=False))
        assert "error" in result

    def test_logout(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_logout
        result = json.loads(handle_logout({}, ig=mock_ig, is_logged_in=True))
        assert result["status"] == "ok"

    def test_logout_not_logged_in(self, mock_ig):
        from instaharvest_v2.agent.tools.auth_tools import handle_logout
        result = json.loads(handle_logout({}, ig=mock_ig, is_logged_in=False))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# ANALYTICS TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestAnalyticsTools:
    def test_engagement_rate(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_engagement_rate
        result = json.loads(handle_get_engagement_rate({"username": "testuser"}, ig=mock_ig))
        assert result["rate"] == 3.5
        mock_ig.analytics.engagement_rate.assert_called_once()

    def test_engagement_rate_no_username(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_engagement_rate
        result = json.loads(handle_get_engagement_rate({}, ig=mock_ig))
        assert "error" in result

    def test_best_posting_times(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_best_posting_times
        result = json.loads(handle_get_best_posting_times({"username": "testuser"}, ig=mock_ig))
        assert "best_hours" in result

    def test_content_analysis(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_content_analysis
        result = json.loads(handle_get_content_analysis({"username": "testuser"}, ig=mock_ig))
        assert result["photo"] == 60

    def test_profile_summary(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_profile_summary
        result = json.loads(handle_get_profile_summary({"username": "testuser"}, ig=mock_ig))
        assert result["followers"] == 10000

    def test_compare_accounts(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_compare_accounts
        result = json.loads(handle_compare_accounts(
            {"usernames": ["user1", "user2"]}, ig=mock_ig
        ))
        assert len(result) == 2

    def test_compare_accounts_too_few(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_compare_accounts
        result = json.loads(handle_compare_accounts(
            {"usernames": ["only_one"]}, ig=mock_ig
        ))
        assert "error" in result

    def test_no_ig_returns_error(self):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_engagement_rate
        result = json.loads(handle_get_engagement_rate({"username": "x"}, ig=None))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# INSIGHTS TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestInsightsTools:
    def test_account_insights(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_account_insights
        result = json.loads(handle_get_account_insights({}, ig=mock_ig, is_logged_in=True))
        assert result["reach"] == 5000

    def test_account_insights_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_account_insights
        result = json.loads(handle_get_account_insights({}, ig=mock_ig, is_logged_in=False))
        assert "error" in result

    def test_media_insight(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_media_insight
        result = json.loads(handle_get_media_insight(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["saves"] == 25

    def test_media_insight_no_id(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_media_insight
        result = json.loads(handle_get_media_insight({}, ig=mock_ig, is_logged_in=True))
        assert "error" in result

    def test_business_info(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_business_info
        result = json.loads(handle_get_business_info(
            {"user_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["category"] == "Fashion"

    def test_ads_accounts(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_ads_accounts
        result = json.loads(handle_get_ads_accounts({}, ig=mock_ig, is_logged_in=True))
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════
# AUDIENCE TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestAudienceTools:
    def test_find_lookalike(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_find_lookalike_audience
        result = json.loads(handle_find_lookalike_audience(
            {"username": "target"}, ig=mock_ig, is_logged_in=True
        ))
        assert len(result) == 2

    def test_audience_overlap(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_audience_overlap
        result = json.loads(handle_get_audience_overlap(
            {"username_a": "user1", "username_b": "user2"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["overlap_pct"] == 12.5

    def test_audience_overlap_missing_user(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_audience_overlap
        result = json.loads(handle_get_audience_overlap(
            {"username_a": "user1"}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result

    def test_audience_insights(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_audience_insights
        result = json.loads(handle_get_audience_insights(
            {"username": "target"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["top_country"] == "US"


# ═══════════════════════════════════════════════════════════
# A/B TEST TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestABTestTools:
    def test_create_ab_test(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_create_ab_test
        result = json.loads(handle_create_ab_test(
            {"variants": ["a", "b"], "metric": "engagement"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["test_id"] == "test_001"

    def test_create_ab_test_too_few_variants(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_create_ab_test
        result = json.loads(handle_create_ab_test(
            {"variants": ["only_one"]}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result

    def test_run_ab_test(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_run_ab_test
        result = json.loads(handle_run_ab_test(
            {"test_id": "test_001"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["status"] == "running"

    def test_get_ab_results(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_get_ab_results
        result = json.loads(handle_get_ab_results(
            {"test_id": "test_001"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["winner"] == "variant_a"

    def test_list_ab_tests(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_list_ab_tests
        result = json.loads(handle_list_ab_tests({}, ig=mock_ig, is_logged_in=True))
        assert len(result) == 1

    def test_ab_test_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.analytics_tools import handle_create_ab_test
        result = json.loads(handle_create_ab_test(
            {"variants": ["a", "b"]}, ig=mock_ig, is_logged_in=False
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# AUTOMATION TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestAutomationTools:
    def test_auto_dm_new_followers(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_dm_new_followers
        result = json.loads(handle_auto_dm_new_followers(
            {"message": "Thanks for following!"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["sent"] == 5

    def test_auto_dm_no_message(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_dm_new_followers
        result = json.loads(handle_auto_dm_new_followers(
            {}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result

    def test_auto_comment_hashtag(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_comment_hashtag
        result = json.loads(handle_auto_comment_hashtag(
            {"hashtag": "fashion", "comment": "Nice!"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["commented"] == 3

    def test_auto_like_feed(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_like_feed
        result = json.loads(handle_auto_like_feed(
            {"max_count": 5}, ig=mock_ig, is_logged_in=True
        ))
        assert result["liked"] == 8

    def test_auto_like_hashtag(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_like_hashtag
        result = json.loads(handle_auto_like_hashtag(
            {"hashtag": "travel"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["liked"] == 6

    def test_auto_watch_stories(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_watch_stories
        result = json.loads(handle_auto_watch_stories(
            {}, ig=mock_ig, is_logged_in=True
        ))
        assert result["watched"] == 15

    def test_get_action_log(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_get_action_log
        result = json.loads(handle_get_action_log({}, ig=mock_ig, is_logged_in=True))
        assert len(result) == 1

    def test_automation_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_auto_like_feed
        result = json.loads(handle_auto_like_feed({}, ig=mock_ig, is_logged_in=False))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# SCHEDULER TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestSchedulerTools:
    def test_schedule_post(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_schedule_post
        result = json.loads(handle_schedule_post(
            {"image_path": "photo.jpg", "caption": "Hello!", "schedule_time": "2024-01-15 10:00"},
            ig=mock_ig, is_logged_in=True
        ))
        assert result["job_id"] == "job_001"

    def test_schedule_post_missing_fields(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_schedule_post
        result = json.loads(handle_schedule_post(
            {"caption": "Hello!"}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result

    def test_schedule_story(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_schedule_story
        result = json.loads(handle_schedule_story(
            {"media_path": "story.jpg", "schedule_time": "2024-01-15 12:00"},
            ig=mock_ig, is_logged_in=True
        ))
        assert result["job_id"] == "job_002"

    def test_schedule_reel(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_schedule_reel
        result = json.loads(handle_schedule_reel(
            {"video_path": "reel.mp4", "caption": "Reel!", "schedule_time": "2024-01-15 14:00"},
            ig=mock_ig, is_logged_in=True
        ))
        assert result["job_id"] == "job_003"

    def test_list_scheduled_jobs(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_list_scheduled_jobs
        result = json.loads(handle_list_scheduled_jobs({}, ig=mock_ig, is_logged_in=True))
        assert len(result) == 1

    def test_cancel_scheduled_job(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_cancel_scheduled_job
        result = json.loads(handle_cancel_scheduled_job(
            {"job_id": "job_001"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["status"] == "cancelled"

    def test_cancel_no_job_id(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_cancel_scheduled_job
        result = json.loads(handle_cancel_scheduled_job({}, ig=mock_ig, is_logged_in=True))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# MONITOR TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestMonitorTools:
    def test_monitor_account(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_monitor_account
        result = json.loads(handle_monitor_account(
            {"username": "target"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["status"] == "watching"

    def test_unmonitor_account(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_unmonitor_account
        result = json.loads(handle_unmonitor_account(
            {"username": "target"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["status"] == "unwatched"

    def test_monitor_check_now(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_monitor_check_now
        result = json.loads(handle_monitor_check_now({}, ig=mock_ig, is_logged_in=True))
        assert result["checked"] == 3

    def test_get_monitor_events(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_get_monitor_events
        result = json.loads(handle_get_monitor_events({}, ig=mock_ig, is_logged_in=True))
        assert len(result) == 1

    def test_get_monitor_events_with_filter(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_get_monitor_events
        result = json.loads(handle_get_monitor_events(
            {"username": "target"}, ig=mock_ig, is_logged_in=True
        ))
        assert len(result) == 1

    def test_get_monitor_stats(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_get_monitor_stats
        result = json.loads(handle_get_monitor_stats({}, ig=mock_ig, is_logged_in=True))
        assert result["watched"] == 5

    def test_monitor_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.automation_tools import handle_monitor_account
        result = json.loads(handle_monitor_account(
            {"username": "target"}, ig=mock_ig, is_logged_in=False
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# PIPELINE TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestPipelineTools:
    def test_pipeline_to_sqlite(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_pipeline_to_sqlite
        result = json.loads(handle_pipeline_to_sqlite(
            {"username": "testuser", "db_path": "test.db"}, ig=mock_ig
        ))
        assert result["rows"] == 150

    def test_pipeline_to_sqlite_no_username(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_pipeline_to_sqlite
        result = json.loads(handle_pipeline_to_sqlite({}, ig=mock_ig))
        assert "error" in result

    def test_pipeline_to_jsonl(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_pipeline_to_jsonl
        result = json.loads(handle_pipeline_to_jsonl(
            {"username": "testuser"}, ig=mock_ig
        ))
        assert result["lines"] == 150


# ═══════════════════════════════════════════════════════════
# BULK DOWNLOAD TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestBulkDownloadTools:
    def test_bulk_download_posts(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_posts
        result = json.loads(handle_bulk_download_posts(
            {"username": "testuser"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["downloaded"] == 50

    def test_bulk_download_stories(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_stories
        result = json.loads(handle_bulk_download_stories(
            {"username": "testuser"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["downloaded"] == 8

    def test_bulk_download_highlights(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_highlights
        result = json.loads(handle_bulk_download_highlights(
            {"username": "testuser"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["downloaded"] == 12

    def test_bulk_download_everything(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_everything
        result = json.loads(handle_bulk_download_everything(
            {"username": "testuser"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["posts"] == 50

    def test_bulk_download_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_posts
        result = json.loads(handle_bulk_download_posts(
            {"username": "testuser"}, ig=mock_ig, is_logged_in=False
        ))
        assert "error" in result

    def test_bulk_download_no_username(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_bulk_download_posts
        result = json.loads(handle_bulk_download_posts(
            {}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# AI SUGGEST TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestAISuggestTools:
    def test_ai_suggest_hashtags(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_ai_suggest_hashtags
        result = json.loads(handle_ai_suggest_hashtags(
            {"caption": "Summer vibes at the beach"}, ig=mock_ig
        ))
        assert "#fashion" in result

    def test_ai_suggest_hashtags_no_caption(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_ai_suggest_hashtags
        result = json.loads(handle_ai_suggest_hashtags({}, ig=mock_ig))
        assert "error" in result

    def test_ai_suggest_captions(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_ai_suggest_captions
        result = json.loads(handle_ai_suggest_captions(
            {"topic": "travel", "style": "funny"}, ig=mock_ig
        ))
        assert len(result) == 2

    def test_ai_suggest_captions_no_topic(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_ai_suggest_captions
        result = json.loads(handle_ai_suggest_captions({}, ig=mock_ig))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# COMMENT MANAGER TOOLS TESTS
# ═══════════════════════════════════════════════════════════

class TestCommentManagerTools:
    def test_manage_comments(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_manage_comments
        result = json.loads(handle_manage_comments(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert len(result) == 1

    def test_manage_comments_no_media_id(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_manage_comments
        result = json.loads(handle_manage_comments({}, ig=mock_ig, is_logged_in=True))
        assert "error" in result

    def test_auto_reply_comments(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_auto_reply_comments
        result = json.loads(handle_auto_reply_comments(
            {"media_id": "12345", "reply": "Thank you!"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["replied"] == 5

    def test_auto_reply_missing_fields(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_auto_reply_comments
        result = json.loads(handle_auto_reply_comments(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert "error" in result

    def test_delete_spam_comments(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_delete_spam_comments
        result = json.loads(handle_delete_spam_comments(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["deleted"] == 3

    def test_get_comment_sentiment(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_get_comment_sentiment
        result = json.loads(handle_get_comment_sentiment(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=True
        ))
        assert result["positive"] == 70

    def test_comment_manager_no_login(self, mock_ig):
        from instaharvest_v2.agent.tools.pipeline_tools import handle_manage_comments
        result = json.loads(handle_manage_comments(
            {"media_id": "12345"}, ig=mock_ig, is_logged_in=False
        ))
        assert "error" in result


# ═══════════════════════════════════════════════════════════
# REGISTRY CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════════

class TestRegistryConsistency:
    def test_all_handlers_have_schemas(self):
        """Every tool in TOOL_HANDLERS must have a schema in base.py."""
        from instaharvest_v2.agent.tools import TOOL_HANDLERS
        from instaharvest_v2.agent.providers.base import instaharvest_v2_TOOLS
        schema_names = {t["name"] for t in instaharvest_v2_TOOLS}
        for name in TOOL_HANDLERS:
            assert name in schema_names, f"Tool '{name}' has no schema in base.py"

    def test_tool_count_minimum(self):
        """Ensure we have at least 150 tools registered."""
        from instaharvest_v2.agent.tools import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) >= 150, f"Expected 150+ tools, got {len(TOOL_HANDLERS)}"

    def test_schema_count_minimum(self):
        """Ensure we have at least 150 schemas."""
        from instaharvest_v2.agent.providers.base import instaharvest_v2_TOOLS
        assert len(instaharvest_v2_TOOLS) >= 150, f"Expected 150+ schemas, got {len(instaharvest_v2_TOOLS)}"

    def test_login_required_tools_in_registry(self):
        """All login-required tools must exist in TOOL_HANDLERS."""
        from instaharvest_v2.agent.tools import TOOL_HANDLERS
        from instaharvest_v2.agent.core import InstaAgent
        for tool_name in InstaAgent._LOGIN_REQUIRED_TOOLS:
            assert tool_name in TOOL_HANDLERS, f"Login-required tool '{tool_name}' missing from TOOL_HANDLERS"

    def test_all_schemas_have_required_fields(self):
        """Every tool schema must have name, description, parameters."""
        from instaharvest_v2.agent.providers.base import instaharvest_v2_TOOLS
        for tool in instaharvest_v2_TOOLS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool '{tool.get('name')}' missing 'description'"
            assert "parameters" in tool, f"Tool '{tool.get('name')}' missing 'parameters'"

    def test_no_duplicate_tool_names(self):
        """No duplicate tool names in schema list."""
        from instaharvest_v2.agent.providers.base import instaharvest_v2_TOOLS
        names = [t["name"] for t in instaharvest_v2_TOOLS]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"Duplicate tool names: {set(duplicates)}"


# ═══════════════════════════════════════════════════════════
# ERROR HANDLING TESTS — ig=None for every module
# ═══════════════════════════════════════════════════════════

class TestNoIgErrorHandling:
    """Every handler should return error JSON when ig=None."""

    def test_auth_no_ig(self):
        from instaharvest_v2.agent.tools.auth_tools import handle_login, handle_validate_session, handle_logout
        for handler in [handle_login, handle_validate_session, handle_logout]:
            result = json.loads(handler({}, ig=None))
            assert "error" in result, f"{handler.__name__} should return error when ig=None"

    def test_analytics_no_ig(self):
        from instaharvest_v2.agent.tools.analytics_tools import (
            handle_get_engagement_rate, handle_get_best_posting_times,
            handle_get_content_analysis, handle_get_profile_summary,
            handle_compare_accounts
        )
        for handler in [handle_get_engagement_rate, handle_get_best_posting_times,
                        handle_get_content_analysis, handle_get_profile_summary,
                        handle_compare_accounts]:
            result = json.loads(handler({"username": "x", "usernames": ["a", "b"]}, ig=None))
            assert "error" in result, f"{handler.__name__} should return error when ig=None"

    def test_automation_no_ig(self):
        from instaharvest_v2.agent.tools.automation_tools import (
            handle_auto_dm_new_followers, handle_auto_like_feed,
            handle_schedule_post, handle_monitor_account,
        )
        for handler in [handle_auto_dm_new_followers, handle_auto_like_feed,
                        handle_schedule_post, handle_monitor_account]:
            result = json.loads(handler({}, ig=None))
            assert "error" in result, f"{handler.__name__} should return error when ig=None"

    def test_pipeline_no_ig(self):
        from instaharvest_v2.agent.tools.pipeline_tools import (
            handle_pipeline_to_sqlite, handle_bulk_download_posts,
            handle_ai_suggest_hashtags, handle_manage_comments,
        )
        for handler in [handle_pipeline_to_sqlite, handle_bulk_download_posts,
                        handle_ai_suggest_hashtags, handle_manage_comments]:
            result = json.loads(handler({}, ig=None))
            assert "error" in result, f"{handler.__name__} should return error when ig=None"
