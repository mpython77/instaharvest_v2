"""
Analytics Tools
===============
Agent tool handlers for analytics, insights, audience analysis, and A/B testing.
Covers: analytics, insights, audience, ab_test API modules.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


# ═══════════════════════════════════════════════════════════
# ANALYTICS — Engagement, posting times, content analysis
# ═══════════════════════════════════════════════════════════

def handle_get_engagement_rate(args: Dict, ig=None, **kw) -> str:
    """Calculate engagement rate for a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        post_count = args.get("post_count", 12)
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.analytics.engagement_rate(username, post_count=post_count)
        if isinstance(result, dict):
            return json.dumps(result, default=str)
        return json.dumps({"engagement_rate": result})
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_best_posting_times(args: Dict, ig=None, **kw) -> str:
    """Analyze best posting times for a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        post_count = args.get("post_count", 30)
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.analytics.best_posting_times(username, post_count=post_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_content_analysis(args: Dict, ig=None, **kw) -> str:
    """Analyze content types and performance."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        post_count = args.get("post_count", 20)
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.analytics.content_analysis(username, post_count=post_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_profile_summary(args: Dict, ig=None, **kw) -> str:
    """Get comprehensive profile summary with analytics."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        post_count = args.get("post_count", 12)
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.analytics.profile_summary(username, post_count=post_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_compare_accounts(args: Dict, ig=None, **kw) -> str:
    """Compare multiple Instagram accounts."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        usernames = args.get("usernames", [])
        post_count = args.get("post_count", 12)
        if not usernames or len(usernames) < 2:
            return json.dumps({"error": "At least 2 usernames required"})

        result = ig.analytics.compare(usernames, post_count=post_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# INSIGHTS — Account & media insights (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_get_account_insights(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get account insights summary."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for account insights"})

    try:
        result = ig.insights.get_account_summary()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_media_insight(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get insights for a specific media."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for media insights"})

    try:
        media_id = args.get("media_id", "")
        if not media_id:
            return json.dumps({"error": "media_id is required"})

        result = ig.insights.get_media_insights(media_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_business_info(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get business account information."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for business info"})

    try:
        user_id = args.get("user_id", "")
        if not user_id:
            return json.dumps({"error": "user_id is required"})

        result = ig.insights.get_business_info(user_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_ads_accounts(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get linked ads accounts."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for ads accounts"})

    try:
        result = ig.insights.get_ads_accounts()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# AUDIENCE — Lookalike, overlap, insights (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_find_lookalike_audience(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Find lookalike audience for a user."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for audience analysis"})

    try:
        username = args.get("username", "")
        max_count = args.get("max_count", 50)
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.audience.find_lookalike(username, max_count=max_count)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_audience_overlap(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Calculate audience overlap between two users."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for audience overlap"})

    try:
        username_a = args.get("username_a", "")
        username_b = args.get("username_b", "")
        if not username_a or not username_b:
            return json.dumps({"error": "username_a and username_b are required"})

        result = ig.audience.overlap(username_a, username_b)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_audience_insights(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get audience demographics and insights."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for audience insights"})

    try:
        username = args.get("username", "")
        if not username:
            return json.dumps({"error": "username is required"})

        result = ig.audience.insights(username)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════
# A/B TESTING (REQUIRES LOGIN)
# ═══════════════════════════════════════════════════════════

def handle_create_ab_test(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Create a new A/B test."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for A/B testing"})

    try:
        variants = args.get("variants", [])
        metric = args.get("metric", "engagement")
        description = args.get("description", "")
        if not variants or len(variants) < 2:
            return json.dumps({"error": "At least 2 variants required"})

        result = ig.ab_test.create(variants=variants, metric=metric, description=description)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_run_ab_test(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Run an A/B test."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for A/B testing"})

    try:
        test_id = args.get("test_id", "")
        if not test_id:
            return json.dumps({"error": "test_id is required"})

        result = ig.ab_test.run(test_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_get_ab_results(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get A/B test results."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for A/B testing"})

    try:
        test_id = args.get("test_id", "")
        if not test_id:
            return json.dumps({"error": "test_id is required"})

        result = ig.ab_test.results(test_id)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_list_ab_tests(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """List all A/B tests."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Login required for A/B testing"})

    try:
        status = args.get("status", None)
        result = ig.ab_test.list_tests(status=status) if status else ig.ab_test.list_tests()
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
