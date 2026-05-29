"""
test_session_manager.py — SessionManager + SessionInfo Tests
==============================================================
Covers: SessionInfo data, cookies, jazoest, fingerprint init,
SessionManager add/get/rotate/error tracking, auto-save, cookie update.
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from instaharvest_v2.session_manager import (
    SessionManager, SessionInfo, SessionFingerprint,
)


# ═══════════════════════════════════════════════════════════
# SessionFingerprint
# ═══════════════════════════════════════════════════════════
class TestSessionFingerprint:
    def test_from_profile(self):
        profile = {
            "user_agent": "Mozilla/5.0 Chrome/142",
            "sec_ch_ua": '"Chrome";v="142"',
            "sec_ch_ua_full_version_list": '"Chrome";v="142.0.0.0"',
            "sec_ch_ua_platform": '"Windows"',
            "sec_ch_ua_platform_version": '"19.0.0"',
            "impersonate": "chrome142",
        }
        fp = SessionFingerprint.from_profile(profile)
        assert fp.user_agent == "Mozilla/5.0 Chrome/142"
        assert fp.impersonate == "chrome142"

    def test_from_user_agent_windows(self):
        fp = SessionFingerprint.from_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/136.0.0.0"
        )
        assert fp.sec_ch_ua_platform == '"Windows"'
        assert "136" in fp.sec_ch_ua
        assert "136" in fp.sec_ch_ua_full_version_list

    def test_from_user_agent_macos(self):
        fp = SessionFingerprint.from_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/142.0.0.0"
        )
        assert fp.sec_ch_ua_platform == '"macOS"'

    def test_from_user_agent_linux(self):
        fp = SessionFingerprint.from_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0.0.0"
        )
        assert fp.sec_ch_ua_platform == '"Linux"'

    def test_from_user_agent_no_chrome_version(self):
        fp = SessionFingerprint.from_user_agent("Mozilla/5.0 Safari")
        assert "142" in fp.sec_ch_ua  # fallback

    def test_pick_random(self):
        fp = SessionFingerprint.pick_random()
        assert isinstance(fp, SessionFingerprint)
        assert fp.user_agent != ""
        assert fp.impersonate != ""

    def test_frozen(self):
        fp = SessionFingerprint.pick_random()
        with pytest.raises(AttributeError):
            fp.user_agent = "new"


# ═══════════════════════════════════════════════════════════
# SessionInfo
# ═══════════════════════════════════════════════════════════
class TestSessionInfo:
    @pytest.fixture
    def session(self):
        s = SessionInfo(
            session_id="sid123", csrf_token="csrf456",
            ds_user_id="12345", mid="MID1", ig_did="DID1",
            datr="DATR1", rur="RUR1", user_agent="Chrome/142",
        )
        s._init_fingerprint()
        return s

    def test_basic_fields(self, session):
        assert session.session_id == "sid123"
        assert session.csrf_token == "csrf456"
        assert session.ds_user_id == "12345"
        assert session.is_active is True
        assert session.is_valid is True

    def test_jazoest(self, session):
        expected = "2" + str(sum(ord(c) for c in "csrf456"))
        assert session.jazoest == expected

    def test_jazoest_empty(self):
        s = SessionInfo(session_id="x", csrf_token="", ds_user_id="1")
        assert s.jazoest == "2"

    def test_cookies_dict(self, session):
        c = session.cookies
        assert c["sessionid"] == "sid123"
        assert c["csrftoken"] == "csrf456"
        assert c["ds_user_id"] == "12345"
        assert c["mid"] == "MID1"
        assert c["ig_did"] == "DID1"
        assert c["datr"] == "DATR1"
        assert c["rur"] == "RUR1"

    def test_cookies_without_optional(self):
        s = SessionInfo(session_id="x", csrf_token="y", ds_user_id="1")
        c = s.cookies
        assert "mid" not in c
        assert "ig_did" not in c

    def test_cookie_string_order(self, session):
        cs = session.cookie_string
        # Check order: ig_did before mid before csrftoken before sessionid
        assert cs.index("ig_did") < cs.index("mid")
        assert cs.index("mid") < cs.index("csrftoken")
        assert cs.index("csrftoken") < cs.index("sessionid")

    def test_to_dict(self, session):
        d = session.to_dict()
        assert d["session_id"] == "sid123"
        assert d["csrf_token"] == "csrf456"
        assert "saved_at" in d
        assert d["total_requests"] == 0

    def test_init_fingerprint(self, session):
        assert session.fingerprint is not None
        assert isinstance(session.fingerprint, SessionFingerprint)

    def test_init_fingerprint_with_ua(self):
        s = SessionInfo(session_id="x", csrf_token="y", ds_user_id="1",
                       user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/136.0.6778.139 Safari/537.36")
        s._init_fingerprint()
        assert s.fingerprint is not None
        assert "136" in s.fingerprint.sec_ch_ua

    def test_init_fingerprint_without_ua(self):
        s = SessionInfo(session_id="x", csrf_token="y", ds_user_id="1")
        s._init_fingerprint()
        assert s.fingerprint is not None
        assert s.user_agent != ""  # Should be set from random profile

    def test_init_fingerprint_idempotent(self, session):
        fp = session.fingerprint
        session._init_fingerprint()
        assert session.fingerprint is fp  # Same object


# ═══════════════════════════════════════════════════════════
# SessionManager
# ═══════════════════════════════════════════════════════════
class TestSessionManager:
    @pytest.fixture
    def sm(self):
        return SessionManager()

    def test_add_session(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        assert isinstance(s, SessionInfo)
        assert sm.session_count == 1
        assert sm.active_count == 1

    def test_get_session_round_robin(self, sm):
        sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.add_session(session_id="s2", csrf_token="c2", ds_user_id="u2")
        s1 = sm.get_session()
        s2 = sm.get_session()
        assert s1.session_id == "s1"
        assert s2.session_id == "s2"
        # Wraps around
        s3 = sm.get_session()
        assert s3.session_id == "s1"

    def test_get_session_none(self, sm):
        assert sm.get_session() is None

    def test_get_session_increments_request_count(self, sm):
        sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        s = sm.get_session()
        # get_session() no longer bumps total_requests — only report_request() does
        # (the counter must reflect actual HTTP dispatches, not session lookups).
        assert s.total_requests == 0
        sm.report_request(s)
        assert s.total_requests == 1
        sm.report_request(s)
        assert s.total_requests == 2

    def test_report_error(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.report_error(s)
        assert s.errors == 1
        assert s.is_active is True

    def test_report_error_deactivates_after_10(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        for _ in range(10):
            sm.report_error(s)
        assert s.is_active is False

    def test_report_login_error_invalidates(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.report_error(s, is_login_error=True)
        assert s.is_valid is False

    def test_report_success(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.report_error(s)
        sm.report_error(s)
        assert s.errors == 2
        sm.report_success(s)
        assert s.errors == 1

    def test_invalidate(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.invalidate(s)
        assert s.is_valid is False
        assert s.is_active is False

    def test_get_all_sessions(self, sm):
        sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        sm.add_session(session_id="s2", csrf_token="c2", ds_user_id="u2")
        assert len(sm.get_all_sessions()) == 2

    def test_reactivation(self, sm):
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        s.is_active = False  # Deactivate
        result = sm.get_session()
        # Should reactivate
        assert result is not None
        assert s.is_active is True


# ═══════════════════════════════════════════════════════════
# Auto-save
# ═══════════════════════════════════════════════════════════
class TestAutoSave:
    def test_save_session(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            sm = SessionManager(auto_save_path=path)
            sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
            assert sm.save_session() is True
            data = json.loads(Path(path).read_text())
            assert data["session_id"] == "s1"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_save_session_no_path(self):
        sm = SessionManager()
        sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        assert sm.save_session() is False

    def test_save_session_no_sessions(self):
        sm = SessionManager(auto_save_path="/tmp/test.json")
        assert sm.save_session() is False

    def test_auto_save_trigger(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            sm = SessionManager(auto_save_path=path, auto_save_interval=2)
            s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
            resp = MagicMock()
            resp.cookies = {}
            resp.headers = {}
            sm.update_from_response(s, resp)  # 1st
            sm.update_from_response(s, resp)  # 2nd → triggers auto-save
            assert Path(path).stat().st_size > 0
        finally:
            Path(path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════
# update_from_response
# ═══════════════════════════════════════════════════════════
class TestUpdateFromResponse:
    def test_cookies_update(self):
        sm = SessionManager()
        s = sm.add_session(session_id="old_sid", csrf_token="old_csrf", ds_user_id="u1")
        resp = MagicMock()
        resp.cookies = {"csrftoken": "new_csrf", "rur": "new_rur"}
        resp.headers = {}
        sm.update_from_response(s, resp)
        assert s.csrf_token == "new_csrf"
        assert s.rur == "new_rur"

    def test_www_claim_update(self):
        sm = SessionManager()
        s = sm.add_session(session_id="s1", csrf_token="c1", ds_user_id="u1")
        resp = MagicMock()
        resp.cookies = {}
        resp.headers = {"x-ig-set-www-claim": "hmac.newclaim"}
        sm.update_from_response(s, resp)
        assert s.ig_www_claim == "hmac.newclaim"

    def test_sessionid_update(self):
        sm = SessionManager()
        s = sm.add_session(session_id="old", csrf_token="c1", ds_user_id="u1")
        resp = MagicMock()
        resp.cookies = {"sessionid": "new_session"}
        resp.headers = {}
        sm.update_from_response(s, resp)
        assert s.session_id == "new_session"


# ═══════════════════════════════════════════════════════════
# reload_from_file
# ═══════════════════════════════════════════════════════════
class TestReloadFromFile:
    def test_reload(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"session_id": "new_sid", "csrf_token": "new_csrf"}, f)
            path = f.name
        try:
            sm = SessionManager(auto_save_path=path)
            s = sm.add_session(session_id="old", csrf_token="old", ds_user_id="u1")
            assert sm.reload_from_file(s) is True
            assert s.session_id == "new_sid"
            assert s.csrf_token == "new_csrf"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_reload_no_path(self):
        sm = SessionManager()
        s = SessionInfo(session_id="x", csrf_token="y", ds_user_id="1")
        assert sm.reload_from_file(s) is False

    def test_reload_no_changes(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"session_id": "same", "csrf_token": "same"}, f)
            path = f.name
        try:
            sm = SessionManager(auto_save_path=path)
            s = sm.add_session(session_id="same", csrf_token="same", ds_user_id="u1")
            assert sm.reload_from_file(s) is False
        finally:
            Path(path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════
# load_from_browser_cookies
# ═══════════════════════════════════════════════════════════
class TestBrowserCookies:
    def test_from_list(self):
        sm = SessionManager()
        cookies = [
            {"name": "sessionid", "value": "sid1", "domain": ".instagram.com"},
            {"name": "csrftoken", "value": "csrf1", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "uid1", "domain": ".instagram.com"},
            {"name": "mid", "value": "mid1", "domain": ".instagram.com"},
            {"name": "other", "value": "val", "domain": ".google.com"},
        ]
        s = sm.load_from_browser_cookies(cookies)
        assert s is not None
        assert s.session_id == "sid1"
        assert s.csrf_token == "csrf1"
        assert s.mid == "mid1"
        assert sm.session_count == 1

    def test_from_file(self):
        cookies = [
            {"name": "sessionid", "value": "sid2", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "uid2", "domain": ".instagram.com"},
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(cookies, f)
            path = f.name
        try:
            sm = SessionManager()
            s = sm.load_from_browser_cookies(path)
            assert s is not None
            assert s.session_id == "sid2"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_sessionid(self):
        sm = SessionManager()
        cookies = [
            {"name": "csrftoken", "value": "c", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "u", "domain": ".instagram.com"},
        ]
        assert sm.load_from_browser_cookies(cookies) is None

    def test_missing_ds_user_id(self):
        sm = SessionManager()
        cookies = [
            {"name": "sessionid", "value": "s", "domain": ".instagram.com"},
        ]
        assert sm.load_from_browser_cookies(cookies) is None

    def test_invalid_source_type(self):
        sm = SessionManager()
        assert sm.load_from_browser_cookies(12345) is None

    def test_rur_quote_stripping(self):
        sm = SessionManager()
        cookies = [
            {"name": "sessionid", "value": "s1", "domain": ".instagram.com"},
            {"name": "ds_user_id", "value": "u1", "domain": ".instagram.com"},
            {"name": "rur", "value": '"ATN\\054123"', "domain": ".instagram.com"},
        ]
        s = sm.load_from_browser_cookies(cookies)
        assert not s.rur.startswith('"')
