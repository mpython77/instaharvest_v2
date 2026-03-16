"""
test_auth_platform_body.py — Full body cover for auth_platform.py (118 miss)
============================================================================
3 functions: _save_debug_response, _extract_page_tokens, resolve_auth_platform
All sync — proper mock session.get/post with realistic responses.
"""
import pytest
import json
import os
from unittest.mock import MagicMock, patch, mock_open

M = MagicMock


# ═══════════════════════════════════════
# _save_debug_response
# ═══════════════════════════════════════
class TestSaveDebugResponse:
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_save_ok(self, mock_dirs, mock_file):
        from instaharvest_v2.auth_platform import _save_debug_response
        _save_debug_response("test.txt", "content here")

    @patch("builtins.open", side_effect=OSError("permission denied"))
    @patch("os.makedirs")
    def test_save_fail(self, mock_dirs, mock_file):
        from instaharvest_v2.auth_platform import _save_debug_response
        _save_debug_response("test.txt", "content here")  # should not raise


# ═══════════════════════════════════════
# _extract_page_tokens
# ═══════════════════════════════════════
class TestExtractPageTokens:
    def test_empty_page(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        tokens = _extract_page_tokens("")
        assert tokens["lsd"] == ""

    def test_full_tokens(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '''
        "LSD",[],{"token":"ABC123"}
        "jazoest":"98765"
        "hsi":"1234567890"
        "server_revision":1033859812
        "__spin_t":1700000000
        "haste_session":"abcdef"
        "__s":"abc:def:ghi"
        "__dyn":"dynvalue"
        "__csr":"csrvalue"
        "__hsdp":"hsdpval"
        "__hblp":"hblpval"
        "__sjsp":"sjspval"
        '''
        tokens = _extract_page_tokens(html)
        assert tokens["lsd"] == "ABC123"
        assert tokens["jazoest"] == "98765"
        assert tokens["hsi"] == "1234567890"
        assert tokens["spin_r"] == "1033859812"
        assert tokens["spin_t"] == "1700000000"
        assert tokens["__hs"] == "abcdef"
        assert tokens["__s"] == "abc:def:ghi"
        assert tokens["__dyn"] == "dynvalue"
        assert tokens["__csr"] == "csrvalue"
        assert tokens["__hsdp"] == "hsdpval"
        assert tokens["__hblp"] == "hblpval"
        assert tokens["__sjsp"] == "sjspval"

    def test_alt_lsd_pattern(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"lsd":{"token":"XYZ789"}'
        tokens = _extract_page_tokens(html)
        assert tokens["lsd"] == "XYZ789"

    def test_alt_lsd_input(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = 'name="lsd" value="INPUT_LSD"'
        tokens = _extract_page_tokens(html)
        assert tokens["lsd"] == "INPUT_LSD"

    def test_alt_jazoest(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = 'jazoest=54321'
        tokens = _extract_page_tokens(html)
        assert tokens["jazoest"] == "54321"

    def test_alt_spin_r(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"__spin_r":999999'
        tokens = _extract_page_tokens(html)
        assert tokens["spin_r"] == "999999"

    def test_alt_hs(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"__hs":"alt_session"'
        tokens = _extract_page_tokens(html)
        assert tokens["__hs"] == "alt_session"


# ═══════════════════════════════════════
# resolve_auth_platform — FULL BODY
# ═══════════════════════════════════════
class TestResolveAuthPlatform:
    def _mock_session(self, graphql_json=None, has_sessionid=False, cookies=None):
        session = M()
        # Page response
        page_resp = M()
        page_resp.text = '''
            "LSD",[],{"token":"test_lsd"}
            "jazoest":"12345"
            "hsi":"999"
            "server_revision":1033859812
            "__spin_t":1700000000
            "haste_session":"hs_val"
        '''
        page_resp.status_code = 200

        # GraphQL response
        gql_resp = M()
        gql_resp.status_code = 200
        gql_resp.text = json.dumps(graphql_json or {})
        gql_resp.json.return_value = graphql_json or {}
        gql_resp.headers = {}

        session.get.return_value = page_resp
        session.post.return_value = gql_resp

        # Cookie jar
        cookie_dict = cookies or {}
        if has_sessionid:
            cookie_dict["sessionid"] = "sess123"
            cookie_dict["ds_user_id"] = "12345"
        cookie_dict.setdefault("csrftoken", "new_csrf")
        session.cookies = M()
        session.cookies.get = lambda k, default="": cookie_dict.get(k, default)
        session.cookies.items.return_value = list(cookie_dict.items())
        session.cookies.keys.return_value = list(cookie_dict.keys())
        return session

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_no_apc_param(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session()
        result = resolve_auth_platform(
            session, "https://www.instagram.com/auth_platform/",
            "csrf", "UA"
        )
        assert result is None

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_no_callback(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session()
        result = resolve_auth_platform(
            session, "https://www.instagram.com/auth_platform/?apc=encrypted123",
            "csrf", "UA", challenge_callback=None
        )
        assert result is None

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_no_code_from_callback(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session()
        result = resolve_auth_platform(
            session, "https://www.instagram.com/auth_platform/?apc=encrypted123",
            "csrf", "UA", challenge_callback=lambda: None, username="test"
        )
        assert result is None

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_success_with_sessionid(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(has_sessionid=True)
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
        assert result is not None
        assert result["status"] == "ok"
        assert result["authenticated"] is True

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_success_via_known_key(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {
                "xfb_auth_platform_submit_code": {
                    "result": "SUCCESS",
                    "redirect_uri": "",
                    "error_message": "",
                    "ap_error_code": "",
                }
            }
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
        assert result is not None
        assert result["challenge_resolved"] is True

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_success_via_redirect(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        # After redirect, sessionid appears
        post_cookies = {"csrftoken": "csrf2", "sessionid": "", "ds_user_id": ""}
        session = self._mock_session(graphql_json={
            "data": {
                "auth_platform_submit_code": {
                    "redirect_uri": "/accounts/login/two_factor/",
                    "result": "",
                    "error_message": "",
                    "ap_error_code": "",
                }
            }
        }, cookies=post_cookies)
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_success_via_dynamic_key(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {
                "new_auth_platform_submit_code_v2": {
                    "result": "",
                    "redirect_uri": "",
                    "error_message": "",
                    "ap_error_code": "",
                }
            }
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_error_response(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {
                "xfb_auth_platform_submit_code": {
                    "result": "",
                    "error_message": "Invalid code",
                    "ap_error_code": "1234",
                }
            },
            "errors": [{"message": "GraphQL error"}]
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_logged_in_user(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {},
            "logged_in_user": {"pk": 12345}
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
        assert result is not None
        assert result["authenticated"] is True

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_non_json_response(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session()
        gql_resp = M()
        gql_resp.status_code = 200
        gql_resp.text = "<html>Redirect page</html>"
        gql_resp.json.side_effect = ValueError("Not JSON")
        gql_resp.headers = {}
        session.post.return_value = gql_resp
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_non_json_with_session(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(has_sessionid=True)
        gql_resp = M()
        gql_resp.status_code = 200
        gql_resp.text = "<html>Redirect page</html>"
        gql_resp.json.side_effect = ValueError("Not JSON")
        gql_resp.headers = {}
        session.post.return_value = gql_resp
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
        assert result is not None
        assert result["authenticated"] is True

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_graphql_request_fail(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session()
        session.post.side_effect = Exception("Network error")
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
        assert result is None

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_checkpoint_page_fail(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(has_sessionid=True)
        session.get.side_effect = Exception("Timeout")
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_data_redirect_uri_fallback(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {
                "redirect_uri": "/accounts/login/",
                "result": "SUCCESS",
            }
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )

    @patch("instaharvest_v2.auth_platform.time.sleep")
    @patch("instaharvest_v2.auth_platform._save_debug_response")
    def test_unexpected_result(self, mock_save, mock_sleep):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        session = self._mock_session(graphql_json={
            "data": {"unknown_key": {"some": "data"}}
        })
        result = resolve_auth_platform(
            session, "/auth_platform/?apc=enc123",
            "csrf", "UA", challenge_callback=lambda: "123456", username="test"
        )
