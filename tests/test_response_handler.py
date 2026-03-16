"""
test_response_handler.py — HTTP Response Handling Tests
========================================================
Tests every HTTP status code path and Instagram error classification.
"""
import pytest
from unittest.mock import MagicMock, patch
from instaharvest_v2.response_handler import ResponseHandler
from instaharvest_v2.session_manager import SessionManager, SessionInfo
from instaharvest_v2.exceptions import (
    LoginRequired, RateLimitError, NotFoundError,
    ChallengeRequired, CheckpointRequired, ConsentRequired,
    PrivateAccountError, NetworkError, InstagramError,
)


@pytest.fixture
def handler():
    sm = MagicMock(spec=SessionManager)
    sm.report_error = MagicMock()
    return ResponseHandler(sm)


@pytest.fixture
def session():
    s = MagicMock(spec=SessionInfo)
    s.ig_www_claim = None
    return s


def _make_response(status_code=200, json_data=None, text="", headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


# ═══════════════════════════════════════════════════════════
# HTTP Status Code Tests
# ═══════════════════════════════════════════════════════════
class TestHttpStatusCodes:
    def test_429_rate_limit(self, handler, session):
        resp = _make_response(429)
        with pytest.raises(RateLimitError) as exc_info:
            handler.handle(resp, session)
        assert exc_info.value.status_code == 429

    def test_401_unauthorized(self, handler, session):
        resp = _make_response(401)
        with pytest.raises(LoginRequired) as exc_info:
            handler.handle(resp, session)
        assert exc_info.value.status_code == 401
        handler._session_mgr.report_error.assert_called_once()

    def test_404_not_found(self, handler, session):
        resp = _make_response(404)
        with pytest.raises(NotFoundError) as exc_info:
            handler.handle(resp, session)
        assert exc_info.value.status_code == 404

    def test_500_server_error(self, handler, session):
        resp = _make_response(500)
        with pytest.raises(NetworkError):
            handler.handle(resp, session)

    def test_502_server_error(self, handler, session):
        resp = _make_response(502)
        with pytest.raises(NetworkError):
            handler.handle(resp, session)

    def test_200_success(self, handler, session):
        resp = _make_response(200, json_data={"status": "ok", "user": {"pk": 1}})
        result = handler.handle(resp, session)
        assert result["status"] == "ok"
        assert result["user"]["pk"] == 1


# ═══════════════════════════════════════════════════════════
# Header Session Update
# ═══════════════════════════════════════════════════════════
class TestSessionUpdate:
    def test_ig_set_www_claim(self, handler, session):
        resp = _make_response(200, json_data={"status": "ok"},
                              headers={"x-ig-set-www-claim": "hmac.claim123"})
        handler.handle(resp, session)
        assert session.ig_www_claim == "hmac.claim123"

    def test_no_claim_header(self, handler, session):
        resp = _make_response(200, json_data={"status": "ok"}, headers={})
        session.ig_www_claim = "old"
        handler.handle(resp, session)
        assert session.ig_www_claim == "old"


# ═══════════════════════════════════════════════════════════
# 400/403 Client Errors
# ═══════════════════════════════════════════════════════════
class TestClientErrors:
    def test_400_require_login(self, handler, session):
        resp = _make_response(400, json_data={"require_login": True})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_400_message_login_required(self, handler, session):
        resp = _make_response(400, json_data={"message": "login_required"})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_400_challenge(self, handler, session):
        resp = _make_response(400, json_data={"challenge": {"url": "/challenge/123/"}})
        with pytest.raises(ChallengeRequired):
            handler.handle(resp, session)

    def test_400_checkpoint(self, handler, session):
        resp = _make_response(400, json_data={"checkpoint_url": "/checkpoint/456/"})
        with pytest.raises(CheckpointRequired):
            handler.handle(resp, session)

    def test_400_consent(self, handler, session):
        resp = _make_response(400, json_data={"consent_required": True})
        with pytest.raises(ConsentRequired):
            handler.handle(resp, session)

    def test_400_spam(self, handler, session):
        resp = _make_response(400, json_data={"spam": True})
        with pytest.raises(RateLimitError):
            handler.handle(resp, session)

    def test_403_login_required_html(self, handler, session):
        resp = _make_response(403, text="login_required fallback")
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_400_generic(self, handler, session):
        resp = _make_response(400, json_data={"message": "unknown_error"})
        with pytest.raises(InstagramError):
            handler.handle(resp, session)


# ═══════════════════════════════════════════════════════════
# _classify_error Message-Based
# ═══════════════════════════════════════════════════════════
class TestClassifyError:
    def test_login_message(self, handler, session):
        with pytest.raises(LoginRequired):
            handler._classify_error("login_required", 400, {}, session)

    def test_useragent_mismatch(self, handler, session):
        with pytest.raises(InstagramError, match="User-Agent mismatch"):
            handler._classify_error("useragent mismatch", 400, {}, session)

    def test_challenge_message(self, handler, session):
        with pytest.raises(ChallengeRequired):
            handler._classify_error("challenge_required", 400, {}, session)

    def test_checkpoint_message(self, handler, session):
        with pytest.raises(CheckpointRequired):
            handler._classify_error("checkpoint_required", 400, {}, session)

    def test_consent_message(self, handler, session):
        with pytest.raises(ConsentRequired):
            handler._classify_error("consent_required", 400, {}, session)

    def test_not_found_message(self, handler, session):
        with pytest.raises(NotFoundError):
            handler._classify_error("user_not_found", 400, {}, session)

    def test_private_message(self, handler, session):
        with pytest.raises(PrivateAccountError):
            handler._classify_error("private account", 400, {}, session)

    def test_empty_message_returns(self, handler, session):
        # Should not raise
        handler._classify_error("", 400, {}, session)


# ═══════════════════════════════════════════════════════════
# JSON Parse Errors
# ═══════════════════════════════════════════════════════════
class TestJsonParseErrors:
    def test_html_login_page(self, handler, session):
        resp = _make_response(200, text="LoginAndSignupPage content here")
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_non_json_non_login(self, handler, session):
        resp = _make_response(200, text="random HTML content")
        with pytest.raises(InstagramError, match="JSON parse error"):
            handler.handle(resp, session)


# ═══════════════════════════════════════════════════════════
# Instagram Internal Errors (status=fail)
# ═══════════════════════════════════════════════════════════
class TestInternalErrors:
    def test_status_fail(self, handler, session):
        resp = _make_response(200, json_data={"status": "fail", "message": "generic fail"})
        with pytest.raises(InstagramError, match="generic fail"):
            handler.handle(resp, session)

    def test_status_fail_login(self, handler, session):
        resp = _make_response(200, json_data={"status": "fail", "message": "login_required"})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_require_login_flag(self, handler, session):
        resp = _make_response(200, json_data={"status": "ok", "require_login": True})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_status_ok_no_error(self, handler, session):
        resp = _make_response(200, json_data={"status": "ok", "items": []})
        result = handler.handle(resp, session)
        assert result["status"] == "ok"


# ═══════════════════════════════════════════════════════════
# 3xx Redirects
# ═══════════════════════════════════════════════════════════
class TestRedirects:
    def test_redirect_with_json(self, handler, session):
        resp = _make_response(301, json_data={"redirect": True},
                              headers={"location": "/somewhere/"})
        result = handler.handle(resp, session)
        assert result == {"redirect": True}

    def test_redirect_to_login(self, handler, session):
        resp = _make_response(302, text="redirect",
                              headers={"location": "/accounts/login/"})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_redirect_no_location(self, handler, session):
        resp = _make_response(302, text="redirect", headers={})
        with pytest.raises(LoginRequired):
            handler.handle(resp, session)

    def test_redirect_to_other(self, handler, session):
        resp = _make_response(301, text="redirect",
                              headers={"location": "/explore/"})
        result = handler.handle(resp, session)
        assert result["redirected"] is True
        assert result["location"] == "/explore/"
