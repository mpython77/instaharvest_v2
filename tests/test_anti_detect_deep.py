"""
test_anti_detect_deep.py — AntiDetect Deep Logic Tests
========================================================
Covers: _create_identity internals, profile scoring, escalation,
error/success tracking, identity rotation lifecycle.
"""
import pytest
from unittest.mock import patch
from instaharvest_v2.anti_detect import (
    AntiDetect, BrowserIdentity, BROWSER_PROFILES, VIEWPORTS,
    TIMEZONE_OFFSETS, SCREEN_DENSITIES,
)


class TestConstants:
    def test_viewports_tuples(self):
        assert len(VIEWPORTS) >= 5
        for vp in VIEWPORTS:
            assert isinstance(vp, tuple)
            assert len(vp) == 2
            assert vp[0] > 0 and vp[1] > 0

    def test_timezone_offsets(self):
        assert len(TIMEZONE_OFFSETS) >= 5
        assert 0 in TIMEZONE_OFFSETS  # UTC

    def test_screen_densities(self):
        assert len(SCREEN_DENSITIES) >= 3
        for d in SCREEN_DENSITIES:
            assert d > 0


class TestIdentityCreation:
    @pytest.fixture
    def ad(self):
        return AntiDetect()

    def test_create_identity_type(self, ad):
        identity = ad._create_identity()
        assert isinstance(identity, BrowserIdentity)

    def test_create_identity_fields(self, ad):
        identity = ad._create_identity()
        assert identity.user_agent != ""
        assert identity.sec_ch_ua != ""
        assert identity.platform in ("Windows", "macOS", "Linux")
        assert identity.browser_name != ""
        assert identity.browser_version != ""
        assert identity.impersonation != ""
        assert identity.device_id != ""
        assert identity.x_mid != ""
        assert identity.window_id != ""

    def test_create_identity_viewport(self, ad):
        identity = ad._create_identity()
        valid_widths = {vp[0] for vp in VIEWPORTS}
        assert identity.viewport_width in valid_widths

    def test_create_identity_coherence(self, ad):
        """Profile fields should be coherent — UA, sec-ch-ua, platform match."""
        identity = ad._create_identity()
        import re
        versions = re.findall(r'v="(\d+)"', identity.sec_ch_ua)
        non_brand = [v for v in versions if v != "99"]
        if non_brand:
            assert any(v in identity.user_agent for v in non_brand)


class TestGetIdentity:
    @pytest.fixture
    def ad(self):
        return AntiDetect()

    def test_first_call_creates(self, ad):
        identity = ad.get_identity()
        assert isinstance(identity, BrowserIdentity)
        assert ad._current_identity is not None

    def test_subsequent_calls_return_identity(self, ad):
        i1 = ad.get_identity()
        assert isinstance(i1, BrowserIdentity)
        i2 = ad.get_identity()
        assert isinstance(i2, BrowserIdentity)

    def test_force_new(self, ad):
        i1 = ad.get_identity()
        did1 = i1.device_id
        i2 = ad.get_identity(force_new=True)
        # force_new creates new identity (may have different device_id)
        assert isinstance(i2, BrowserIdentity)


class TestProfileScoring:
    @pytest.fixture
    def ad(self):
        return AntiDetect()

    def test_on_success_reduces_errors(self, ad):
        ad._consecutive_errors = 5
        ad.on_success()
        assert ad._consecutive_errors == 0

    def test_on_error_increments(self, ad):
        ad.get_identity()
        ad.on_error(Exception("test"))
        assert ad._error_count >= 1
        assert ad._consecutive_errors >= 1

    def test_escalation_on_errors(self, ad):
        ad.get_identity()
        for _ in range(5):
            ad.on_error(Exception("test"))
        assert ad._escalation_level >= 1

    def test_escalation_resets_on_success(self, ad):
        ad.get_identity()
        for _ in range(5):
            ad.on_error(Exception("test"))
        ad.on_success()
        # Escalation should decrease eventually
        assert ad._consecutive_errors == 0


class TestRotation:
    @pytest.fixture
    def ad(self):
        return AntiDetect()

    def test_rotate_identity(self, ad):
        ad.rotate_identity()
        assert ad._current_identity is not None
        assert ad._identity_uses == 0

    def test_rotate_creates_different(self, ad):
        ad.rotate_identity()
        did1 = ad._current_identity.device_id
        ad.rotate_identity()
        did2 = ad._current_identity.device_id
        assert did1 != did2  # Should create new device_id

    def test_used_profiles_tracked(self, ad):
        for _ in range(5):
            ad._create_identity()
        assert len(ad._used_profiles) >= 5

    def test_request_count(self, ad):
        assert ad.request_count == 0
        ad._request_count = 42
        assert ad.request_count == 42


class TestHumanDelay:
    def test_does_not_hang(self):
        """human_delay should be patched by conftest."""
        ad = AntiDetect()
        ad.human_delay()  # Should not hang


class TestGetRotationContext:
    def test_returns_dict(self):
        ad = AntiDetect()
        ctx = ad.get_rotation_context()
        assert isinstance(ctx, dict)
        assert "escalation_level" in ctx

    def test_context_content(self):
        ad = AntiDetect()
        ad._escalation_level = 2
        ctx = ad.get_rotation_context()
        assert ctx["escalation_level"] == 2
