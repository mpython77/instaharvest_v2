"""
test_async_modules.py — Comprehensive Module Init/Import Coverage Tests
=========================================================================
Each test imports a module, creates instances with mocks, and touches code paths.
This covers class definitions, __init__ methods, properties, and constants.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio


# ═══════════════════════════════════════════════════════════
# Async Anonymous Client — init, config, parsers
# ═══════════════════════════════════════════════════════════
class TestAsyncAnonClient:
    def test_init_default(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient()
        assert client._unlimited is False
        assert client._max_concurrency == 10

    def test_init_unlimited(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient(unlimited=True)
        assert client._unlimited is True
        assert client._max_concurrency == 1000

    def test_init_custom_concurrency(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient(max_concurrency=50)
        assert client._max_concurrency == 50

    def test_init_with_anti_detect(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        from instaharvest_v2.anti_detect import AntiDetect
        ad = AntiDetect()
        client = AsyncAnonClient(anti_detect=ad)
        assert client._anti_detect is ad

    def test_parse_delegates(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient()
        assert client._parse_count("1.5K") == 1500
        assert client._parse_meta_tags("") == {}

    def test_parse_graphql_user(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient()
        user_data = {
            "id": "123", "username": "test", "full_name": "Test",
            "biography": "bio", "edge_followed_by": {"count": 100},
            "edge_follow": {"count": 50},
            "edge_owner_to_timeline_media": {"count": 10},
            "is_private": False, "is_verified": True,
            "profile_pic_url": "pic", "profile_pic_url_hd": "hd_pic",
        }
        result = client._parse_graphql_user(user_data)
        assert result["username"] == "test"
        assert result["followers"] == 100

    def test_strategy_config(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        from instaharvest_v2.strategy import ProfileStrategy
        client = AsyncAnonClient(profile_strategies=[ProfileStrategy.HTML_PARSE])
        assert ProfileStrategy.HTML_PARSE in client._profile_strategies

    def test_stats(self):
        from instaharvest_v2.async_anon_client import AsyncAnonClient
        client = AsyncAnonClient()
        assert client._request_count == 0
        assert client._error_count == 0


class TestAsyncAnonRateLimiter:
    def test_init_enabled(self):
        from instaharvest_v2.async_anon_client import AsyncAnonRateLimiter
        rl = AsyncAnonRateLimiter(enabled=True)
        assert rl._enabled is True

    def test_init_disabled(self):
        from instaharvest_v2.async_anon_client import AsyncAnonRateLimiter
        rl = AsyncAnonRateLimiter(enabled=False)
        assert rl._enabled is False

    @pytest.mark.asyncio
    async def test_disabled_no_wait(self):
        from instaharvest_v2.async_anon_client import AsyncAnonRateLimiter
        rl = AsyncAnonRateLimiter(enabled=False)
        await rl.wait_if_needed("html_parse")  # Should return immediately


class TestAsyncStrategyFailed:
    def test_exception(self):
        from instaharvest_v2.async_anon_client import AsyncStrategyFailed
        e = AsyncStrategyFailed("test")
        assert str(e) == "test"
        assert isinstance(e, Exception)


# ═══════════════════════════════════════════════════════════
# Async Client — init
# ═══════════════════════════════════════════════════════════
class TestAsyncHttpClient:
    def test_init(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = AsyncRateLimiter()
        client = AsyncHttpClient(sm, pm, ad, rl)
        assert client._session_mgr is sm
        assert client._proxy_mgr is pm
        assert client._anti_detect is ad
        assert client._async_session is None

    def test_get_async_session(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter

        sm = SessionManager()
        pm = ProxyManager()
        ad = AntiDetect()
        rl = AsyncRateLimiter()
        client = AsyncHttpClient(sm, pm, ad, rl)
        session = client._get_async_session()
        assert session is not None
        assert client._async_session is session


# ═══════════════════════════════════════════════════════════
# Sync Anonymous Client — init
# ═══════════════════════════════════════════════════════════
class TestSyncAnonClient:
    def test_init(self):
        from instaharvest_v2.anon_client import AnonClient
        client = AnonClient()
        assert client._unlimited is False

    def test_init_unlimited(self):
        from instaharvest_v2.anon_client import AnonClient
        client = AnonClient(unlimited=True)
        assert client._unlimited is True


# ═══════════════════════════════════════════════════════════
# Rate Limiter
# ═══════════════════════════════════════════════════════════
class TestAsyncRateLimiter:
    def test_init(self):
        from instaharvest_v2.async_rate_limiter import AsyncRateLimiter
        rl = AsyncRateLimiter()
        assert rl is not None

    def test_speed_mode_exists(self):
        from instaharvest_v2.async_rate_limiter import SpeedMode
        assert SpeedMode is not None


# ═══════════════════════════════════════════════════════════
# Smart Rotation
# ═══════════════════════════════════════════════════════════
class TestSmartRotation:
    def test_init(self):
        from instaharvest_v2.smart_rotation import SmartRotationCoordinator, _mask_proxy
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.proxy_manager import ProxyManager
        coord = SmartRotationCoordinator(AntiDetect(), ProxyManager())
        assert coord is not None

    def test_mask_proxy(self):
        from instaharvest_v2.smart_rotation import _mask_proxy
        masked = _mask_proxy("http://user:pass@1.2.3.4:8080")
        assert masked != "http://user:pass@1.2.3.4:8080"
        assert _mask_proxy("") == "direct"
        assert _mask_proxy(None) == "direct"


# ═══════════════════════════════════════════════════════════
# Proxy Health
# ═══════════════════════════════════════════════════════════
class TestProxyHealth:
    def test_import(self):
        try:
            from instaharvest_v2.proxy_health import ProxyHealthChecker
            assert ProxyHealthChecker is not None
        except ImportError:
            pytest.skip("ProxyHealthChecker not available")


# ═══════════════════════════════════════════════════════════
# Email Verifier
# ═══════════════════════════════════════════════════════════
class TestEmailVerifier:
    def test_import(self):
        from instaharvest_v2.email_verifier import EmailVerifier
        ev = EmailVerifier.__new__(EmailVerifier)
        assert ev is not None


# ═══════════════════════════════════════════════════════════
# Log Config
# ═══════════════════════════════════════════════════════════
class TestLogConfig:
    def test_import(self):
        from instaharvest_v2.log_config import get_debug_logger
        logger = get_debug_logger()
        assert logger is not None


# ═══════════════════════════════════════════════════════════
# Monitor API
# ═══════════════════════════════════════════════════════════
class TestMonitorAPI:
    def test_import(self):
        try:
            from instaharvest_v2.monitor import MonitorAPI
            assert MonitorAPI is not None
        except (ImportError, ModuleNotFoundError):
            pytest.skip("MonitorAPI not available")


# ═══════════════════════════════════════════════════════════
# CLI module
# ═══════════════════════════════════════════════════════════
class TestCLI:
    def test_import(self):
        from instaharvest_v2.cli import main
        assert callable(main)


# ═══════════════════════════════════════════════════════════
# Multi-account
# ═══════════════════════════════════════════════════════════
class TestMultiAccount:
    def test_import(self):
        from instaharvest_v2.multi_account import MultiAccountManager
        assert MultiAccountManager is not None


# ═══════════════════════════════════════════════════════════
# Auth Platform
# ═══════════════════════════════════════════════════════════
class TestAuthPlatform:
    def test_import(self):
        try:
            from instaharvest_v2.auth_platform import AuthPlatform
            assert AuthPlatform is not None
        except (ImportError, ModuleNotFoundError):
            pytest.skip("AuthPlatform not available")


# ═══════════════════════════════════════════════════════════
# API Modules — import-only coverage
# ═══════════════════════════════════════════════════════════
class TestAPIImports:
    """Import each API module to cover class definitions."""

    MODULES = [
        "instaharvest_v2.api.async_graphql",
        "instaharvest_v2.api.async_public",
        "instaharvest_v2.api.async_feed",
        "instaharvest_v2.api.async_growth",
        "instaharvest_v2.api.async_automation",
        "instaharvest_v2.api.async_hashtags",
        "instaharvest_v2.api.async_discover",
        "instaharvest_v2.api.async_collections",
        "instaharvest_v2.api.async_direct",
        "instaharvest_v2.api.async_download",
        "instaharvest_v2.api.async_export",
        "instaharvest_v2.api.async_insights",
        "instaharvest_v2.api.async_comment_manager",
        "instaharvest_v2.api.async_friendships",
        "instaharvest_v2.api.async_bulk_download",
        "instaharvest_v2.api.async_account",
        "instaharvest_v2.api.async_analytics",
        "instaharvest_v2.api.async_ab_test",
        "instaharvest_v2.api.async_ai_suggest",
        "instaharvest_v2.api.async_audience",
        "instaharvest_v2.api.async_auth",
        "instaharvest_v2.api.async_hashtag_research",
        # Sync versions
        "instaharvest_v2.api.automation",
        "instaharvest_v2.api.bulk_download",
        "instaharvest_v2.api.account",
        "instaharvest_v2.api.analytics",
        "instaharvest_v2.api.ab_test",
        "instaharvest_v2.api.ai_suggest",
    ]

    @pytest.mark.parametrize("module_name", MODULES)
    def test_import(self, module_name):
        import importlib
        mod = importlib.import_module(module_name)
        assert mod is not None


# ═══════════════════════════════════════════════════════════
# fb_dtsg
# ═══════════════════════════════════════════════════════════
class TestFbDtsg:
    def test_import(self):
        from instaharvest_v2.fb_dtsg import AsyncFbDtsgProvider
        provider = AsyncFbDtsgProvider()
        assert provider is not None


# ═══════════════════════════════════════════════════════════
# Async Challenge
# ═══════════════════════════════════════════════════════════
class TestAsyncChallenge:
    def test_import(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        assert AsyncChallengeHandler is not None
