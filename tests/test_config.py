"""
test_config.py — Configuration Constants Tests
================================================
Validates all config constants, data structures, and value constraints.
"""
import pytest
from instaharvest_v2 import config


class TestBaseConfig:
    def test_base_url(self):
        assert config.BASE_URL == "https://www.instagram.com"

    def test_api_base(self):
        assert config.API_BASE.startswith("https://www.instagram.com/api/v1")

    def test_ig_app_id(self):
        assert config.IG_APP_ID.isdigit()
        assert len(config.IG_APP_ID) > 10

    def test_ig_app_id_mobile(self):
        assert config.IG_APP_ID_MOBILE.isdigit()
        assert config.IG_APP_ID_MOBILE != config.IG_APP_ID


class TestBrowserImpersonations:
    def test_list_not_empty(self):
        assert len(config.BROWSER_IMPERSONATIONS) >= 3

    def test_all_strings(self):
        for imp in config.BROWSER_IMPERSONATIONS:
            assert isinstance(imp, str)
            assert "chrome" in imp


class TestUserAgents:
    def test_list_not_empty(self):
        assert len(config.USER_AGENTS) >= 3

    def test_all_contain_chrome(self):
        for ua in config.USER_AGENTS:
            assert "Chrome" in ua

    def test_variety(self):
        platforms = set()
        for ua in config.USER_AGENTS:
            if "Windows" in ua: platforms.add("Windows")
            elif "Macintosh" in ua: platforms.add("Mac")
            elif "Linux" in ua: platforms.add("Linux")
        assert len(platforms) >= 2


class TestAcceptLanguages:
    def test_list_not_empty(self):
        assert len(config.ACCEPT_LANGUAGES) >= 3

    def test_all_contain_en(self):
        for lang in config.ACCEPT_LANGUAGES:
            assert "en" in lang


class TestSecChUa:
    def test_list_not_empty(self):
        assert len(config.SEC_CH_UA_VARIANTS) >= 2

    def test_all_contain_chrome(self):
        for sc in config.SEC_CH_UA_VARIANTS:
            assert "Chrome" in sc or "Chromium" in sc


class TestSessionUaProfiles:
    def test_list_not_empty(self):
        assert len(config.SESSION_UA_PROFILES) >= 5

    def test_profile_fields(self):
        required = ["user_agent", "sec_ch_ua", "sec_ch_ua_full_version_list",
                     "sec_ch_ua_platform", "sec_ch_ua_platform_version", "impersonate"]
        for profile in config.SESSION_UA_PROFILES:
            for field in required:
                assert field in profile, f"Missing {field} in profile"

    def test_all_chrome142(self):
        for profile in config.SESSION_UA_PROFILES:
            assert profile["impersonate"] == "chrome142"
            assert "142" in profile["sec_ch_ua"]


class TestRateLimits:
    def test_get_limits(self):
        assert "get_default" in config.RATE_LIMITS
        assert "get_profile" in config.RATE_LIMITS
        assert "calls" in config.RATE_LIMITS["get_default"]
        assert "period" in config.RATE_LIMITS["get_default"]

    def test_post_limits(self):
        assert "post_like" in config.RATE_LIMITS
        assert "post_comment" in config.RATE_LIMITS

    def test_post_stricter_than_get(self):
        get_rate = config.RATE_LIMITS["get_default"]["calls"] / config.RATE_LIMITS["get_default"]["period"]
        post_rate = config.RATE_LIMITS["post_default"]["calls"] / config.RATE_LIMITS["post_default"]["period"]
        assert post_rate < get_rate


class TestRequestDelays:
    def test_min_max(self):
        assert config.REQUEST_DELAYS["min"] < config.REQUEST_DELAYS["max"]

    def test_after_error_higher(self):
        assert config.REQUEST_DELAYS["after_error"]["min"] > config.REQUEST_DELAYS["max"]

    def test_after_rate_limit_highest(self):
        assert config.REQUEST_DELAYS["after_rate_limit"]["min"] > config.REQUEST_DELAYS["after_error"]["max"]


class TestRetrySettings:
    def test_max_retries(self):
        assert config.MAX_RETRIES >= 1

    def test_retry_status_codes(self):
        assert 429 in config.RETRY_STATUS_CODES
        assert 500 in config.RETRY_STATUS_CODES


class TestTimeouts:
    def test_timeouts(self):
        assert config.REQUEST_TIMEOUT > 0
        assert config.CONNECT_TIMEOUT > 0
        assert config.REQUEST_TIMEOUT > config.CONNECT_TIMEOUT


class TestProxySettings:
    def test_health_check_interval(self):
        assert config.PROXY_HEALTH_CHECK_INTERVAL > 0

    def test_max_failures(self):
        assert config.PROXY_MAX_FAILURES >= 1

    def test_min_score(self):
        assert 0 < config.PROXY_MIN_SCORE < 1


class TestAnonConfig:
    def test_anon_rate_limits(self):
        assert len(config.ANON_RATE_LIMITS) >= 5
        for key, val in config.ANON_RATE_LIMITS.items():
            assert "requests" in val
            assert "window" in val

    def test_anon_unlimited(self):
        for val in config.ANON_RATE_LIMITS_UNLIMITED.values():
            assert val["requests"] > 100000

    def test_anon_graphql_hashes(self):
        assert len(config.ANON_GRAPHQL_HASHES) >= 3
        for key, h in config.ANON_GRAPHQL_HASHES.items():
            assert len(h) == 32  # MD5

    def test_graphql_doc_ids(self):
        assert "media_shortcode" in config.GRAPHQL_DOC_IDS
        assert config.GRAPHQL_DOC_IDS["media_shortcode"].isdigit()

    def test_embed_url(self):
        assert "{shortcode}" in config.EMBED_URL

    def test_mobile_api_base(self):
        assert "i.instagram.com" in config.MOBILE_API_BASE

    def test_anon_delays(self):
        assert config.ANON_REQUEST_DELAYS["min"] > 0
        assert config.ANON_REQUEST_DELAYS["min"] < config.ANON_REQUEST_DELAYS["max"]

    def test_anon_delays_unlimited(self):
        assert config.ANON_REQUEST_DELAYS_UNLIMITED["min"] == 0
        assert config.ANON_REQUEST_DELAYS_UNLIMITED["max"] == 0
