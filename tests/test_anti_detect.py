"""
test_anti_detect.py — Anti-Detection System Tests
===================================================
Tests BrowserIdentity, BROWSER_PROFILES coherence, AntiDetect rotation.
"""
import re
import pytest
from unittest.mock import patch, MagicMock
from instaharvest_v2.anti_detect import (
    AntiDetect,
    BrowserIdentity,
    BROWSER_PROFILES,
)
from instaharvest_v2.config import IG_APP_ID


# ═══════════════════════════════════════════════════════════
# BrowserIdentity dataclass
# ═══════════════════════════════════════════════════════════
class TestBrowserIdentity:
    def test_create(self):
        bi = BrowserIdentity(
            user_agent="Mozilla/5.0 Chrome/131",
            sec_ch_ua='"Chrome";v="131"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
            accept_language="en-US",
            viewport_width=1920,
            viewport_height=1080,
            platform="Windows",
            browser_name="chrome",
            browser_version="131",
            impersonation="chrome131",
            device_id="dev1",
            x_mid="mid1",
            window_id="win1",
        )
        assert bi.user_agent == "Mozilla/5.0 Chrome/131"
        assert bi.viewport_width == 1920
        assert bi.platform == "Windows"
        assert bi.browser_name == "chrome"
        assert bi.impersonation == "chrome131"


# ═══════════════════════════════════════════════════════════
# Config constants
# ═══════════════════════════════════════════════════════════
class TestConfigConstants:
    def test_browser_profiles_exist(self):
        assert len(BROWSER_PROFILES) >= 3

    def test_browser_profile_fields(self):
        for profile in BROWSER_PROFILES:
            assert "ua" in profile, f"Profile missing 'ua': {profile}"
            assert "sec_ch_ua" in profile, f"Profile missing 'sec_ch_ua': {profile}"
            assert "platform" in profile, f"Profile missing 'platform': {profile}"

    def test_browser_profile_ua_coherence(self):
        """UA string should contain the Chrome version from sec_ch_ua."""
        for profile in BROWSER_PROFILES:
            ua = profile["ua"]
            sec_ch_ua = profile["sec_ch_ua"]
            versions = re.findall(r'v="(\d+)"', sec_ch_ua)
            chrome_versions = [v for v in versions if v != "99"]
            if chrome_versions:
                assert any(v in ua for v in chrome_versions), \
                    f"UA '{ua[:50]}' doesn't match sec_ch_ua version {chrome_versions}"

    def test_ig_app_id(self):
        assert IG_APP_ID.isdigit()
        assert len(IG_APP_ID) > 10


# ═══════════════════════════════════════════════════════════
# AntiDetect class
# ═══════════════════════════════════════════════════════════
class TestAntiDetect:
    @pytest.fixture
    def ad(self):
        return AntiDetect()

    def test_init(self, ad):
        assert ad is not None
        assert hasattr(ad, "_current_identity")

    def test_rotate_identity(self, ad):
        ad.rotate_identity()
        assert ad._current_identity is not None
        assert isinstance(ad._current_identity, BrowserIdentity)

    def test_rotate_identity_produces_valid_fields(self, ad):
        ad.rotate_identity()
        identity = ad._current_identity
        assert identity.user_agent != ""
        assert identity.sec_ch_ua != ""
        assert identity.platform in ("Windows", "macOS", "Linux")
        assert identity.viewport_width > 0
        assert identity.viewport_height > 0

    def test_rotate_identity_uniqueness(self, ad):
        """Multiple calls should produce at least some variation."""
        device_ids = set()
        for _ in range(10):
            ad.rotate_identity()
            device_ids.add(ad._current_identity.device_id)
        assert len(device_ids) >= 2, "Should generate unique device IDs"

    def test_get_request_headers(self, ad):
        ad.rotate_identity()
        headers = ad.get_request_headers(csrf_token="test_token")
        assert isinstance(headers, dict)
        assert "user-agent" in headers or "User-Agent" in headers
        # x-ig-app-id should be present
        assert any("ig-app-id" in k.lower() for k in headers)

    def test_get_post_headers(self, ad):
        ad.rotate_identity()
        headers = ad.get_post_headers(csrf_token="test_token")
        assert isinstance(headers, dict)

    def test_get_rotation_context(self, ad):
        ctx = ad.get_rotation_context()
        assert isinstance(ctx, dict)

    def test_on_success(self, ad):
        ad.on_success()

    def test_on_error(self, ad):
        ad.on_error(Exception("test error"))

    def test_human_delay_patched(self, ad):
        """human_delay should be patched by conftest — no actual sleep."""
        ad.human_delay()

    def test_identity_platform_consistency(self, ad):
        """Platform in identity should be coherent with UA."""
        ad.rotate_identity()
        identity = ad._current_identity
        ua = identity.user_agent.lower()
        platform = identity.platform
        if platform == "Windows":
            assert "windows" in ua
        elif platform == "macOS":
            assert "mac" in ua or "macintosh" in ua
        elif platform == "Linux":
            assert "linux" in ua

    def test_request_count_increments(self, ad):
        """request_count should be trackable."""
        assert hasattr(ad, "request_count")
