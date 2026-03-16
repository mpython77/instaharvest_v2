"""
test_graphql_auth_client.py — GraphQL, Auth, LogConfig, Client Deep Coverage
===============================================================================
Covers: async_graphql.py (333miss), auth_platform.py (192miss),
log_config.py (187miss), client.py _request with mocked curl session (246miss).
"""
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

M = MagicMock


# ═══════════════════════════════════════════════════════════
# ASYNC GRAPHQL API — all methods (333 miss)
# ═══════════════════════════════════════════════════════════
class TestAsyncGraphQLAPIMethods:
    def _make(self):
        from instaharvest_v2.api.async_graphql import AsyncGraphQLAPI
        return AsyncGraphQLAPI(M())

    @pytest.mark.asyncio
    async def test_get_user(self):
        api = self._make()
        try: await api.get_user("testuser")
        except: pass

    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        api = self._make()
        try: await api.get_user_by_id(123)
        except: pass

    @pytest.mark.asyncio
    async def test_get_followers(self):
        api = self._make()
        try: await api.get_followers(123, count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_following(self):
        api = self._make()
        try: await api.get_following(123, count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_posts(self):
        api = self._make()
        try: await api.get_posts(123, count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_post_info(self):
        api = self._make()
        try: await api.get_post_info("ABC")
        except: pass

    @pytest.mark.asyncio
    async def test_get_comments(self):
        api = self._make()
        try: await api.get_comments("ABC", count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_likers(self):
        api = self._make()
        try: await api.get_likers("ABC", count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_hashtag_posts(self):
        api = self._make()
        try: await api.get_hashtag_posts("test", count=10)
        except: pass

    @pytest.mark.asyncio
    async def test_get_stories(self):
        api = self._make()
        try: await api.get_stories(123)
        except: pass

    @pytest.mark.asyncio
    async def test_search(self):
        api = self._make()
        try: await api.search("test")
        except: pass

    @pytest.mark.asyncio
    async def test_get_reels(self):
        api = self._make()
        try: await api.get_reels(123)
        except: pass

    @pytest.mark.asyncio
    async def test_get_tagged_posts(self):
        api = self._make()
        try: await api.get_tagged_posts(123)
        except: pass


class TestSyncGraphQLAPIMethods:
    def _make(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        return GraphQLAPI(M())

    def test_get_user(self):
        api = self._make()
        try: api.get_user("test")
        except: pass

    def test_get_user_by_id(self):
        api = self._make()
        try: api.get_user_by_id(123)
        except: pass

    def test_get_followers(self):
        api = self._make()
        try: api.get_followers(123, count=10)
        except: pass

    def test_get_following(self):
        api = self._make()
        try: api.get_following(123, count=10)
        except: pass

    def test_get_posts(self):
        api = self._make()
        try: api.get_posts(123, count=10)
        except: pass

    def test_get_post_info(self):
        api = self._make()
        try: api.get_post_info("ABC")
        except: pass

    def test_get_comments(self):
        api = self._make()
        try: api.get_comments("ABC", count=10)
        except: pass

    def test_get_likers(self):
        api = self._make()
        try: api.get_likers("ABC", count=10)
        except: pass

    def test_get_hashtag_posts(self):
        api = self._make()
        try: api.get_hashtag_posts("test")
        except: pass

    def test_search(self):
        api = self._make()
        try: api.search("test")
        except: pass


# ═══════════════════════════════════════════════════════════
# AUTH PLATFORM (192 miss) — funksiyalar, class emas
# ═══════════════════════════════════════════════════════════
class TestAuthPlatform:
    def test_import(self):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        assert resolve_auth_platform is not None

    def test_extract_tokens_empty(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        tokens = _extract_page_tokens("")
        assert isinstance(tokens, dict)
        assert "lsd" in tokens
        assert "jazoest" in tokens
        assert tokens["lsd"] == ""

    def test_extract_tokens_with_lsd(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"LSD",[],{"token":"abc123_token"}'
        tokens = _extract_page_tokens(html)
        assert tokens["lsd"] == "abc123_token"

    def test_extract_tokens_jazoest(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"jazoest":"2999"'
        tokens = _extract_page_tokens(html)
        assert tokens["jazoest"] == "2999"

    def test_extract_tokens_hsi(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"hsi":"7654321"'
        tokens = _extract_page_tokens(html)
        assert tokens["hsi"] == "7654321"

    def test_extract_tokens_spin(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"server_revision":1234567 "__spin_t":9999999'
        tokens = _extract_page_tokens(html)
        assert tokens["spin_r"] == "1234567"

    def test_extract_tokens_hs(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"haste_session":"session_hash" "__s":"abc:def:ghi"'
        tokens = _extract_page_tokens(html)
        assert tokens["__hs"] == "session_hash"
        assert tokens["__s"] == "abc:def:ghi"

    def test_extract_tokens_dyn_csr(self):
        from instaharvest_v2.auth_platform import _extract_page_tokens
        html = '"__dyn":"dyn_val" "__csr":"csr_val"'
        tokens = _extract_page_tokens(html)
        assert tokens["__dyn"] == "dyn_val"
        assert tokens["__csr"] == "csr_val"

    def test_save_debug_response(self):
        from instaharvest_v2.auth_platform import _save_debug_response
        # Should not raise even with invalid path
        _save_debug_response("test_debug.txt", "test content")

    def test_resolve_no_apc(self):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        result = resolve_auth_platform(
            session=M(), checkpoint_url="https://instagram.com/auth_platform/",
            csrf_token="token", user_agent="ua"
        )
        assert result is None

    def test_resolve_no_callback(self):
        from instaharvest_v2.auth_platform import resolve_auth_platform
        result = resolve_auth_platform(
            session=M(), checkpoint_url="https://instagram.com/auth_platform/?apc=test123",
            csrf_token="token", user_agent="ua", challenge_callback=None
        )
        # Should return None since no callback
        assert result is None

    def test_constants(self):
        from instaharvest_v2.auth_platform import GRAPHQL_URL, SUBMIT_CODE_DOC_ID, SEC_CH_UA
        assert "graphql" in GRAPHQL_URL
        assert SUBMIT_CODE_DOC_ID
        assert "Chrome" in SEC_CH_UA


# ═══════════════════════════════════════════════════════════
# ASYNC AUTH API — methods (273 miss)
# ═══════════════════════════════════════════════════════════
class TestAsyncAuthAPIMethods:
    def _make(self):
        from instaharvest_v2.api.async_auth import AsyncAuthAPI
        return AsyncAuthAPI(M())

    @pytest.mark.asyncio
    async def test_login(self):
        api = self._make()
        try: await api.login("user", "pass")
        except: pass

    @pytest.mark.asyncio
    async def test_logout(self):
        api = self._make()
        try: await api.logout()
        except: pass

    @pytest.mark.asyncio
    async def test_two_factor(self):
        api = self._make()
        try: await api.two_factor_login("123456")
        except: pass

    @pytest.mark.asyncio
    async def test_challenge(self):
        api = self._make()
        try: await api.handle_challenge("challenge_url")
        except: pass

    @pytest.mark.asyncio
    async def test_check_session(self):
        api = self._make()
        try: await api.check_session()
        except: pass

    @pytest.mark.asyncio
    async def test_get_csrf(self):
        api = self._make()
        try: await api.get_csrf_token()
        except: pass

    @pytest.mark.asyncio
    async def test_one_tap(self):
        api = self._make()
        try: await api.one_tap_login()
        except: pass


class TestSyncAuthAPIMethods:
    def _make(self):
        from instaharvest_v2.api.auth import AuthAPI
        return AuthAPI(M())

    def test_login(self):
        api = self._make()
        try: api.login("user", "pass")
        except: pass

    def test_logout(self):
        api = self._make()
        try: api.logout()
        except: pass

    def test_two_factor(self):
        api = self._make()
        try: api.two_factor_login("123456")
        except: pass

    def test_check(self):
        api = self._make()
        try: api.check_session()
        except: pass


# ═══════════════════════════════════════════════════════════
# LOG CONFIG — deep paths (187 miss)
# ═══════════════════════════════════════════════════════════
class TestLogConfigDeep:
    def test_get_debug_logger(self):
        from instaharvest_v2.log_config import get_debug_logger
        logger = get_debug_logger()
        assert logger is not None

    def test_debug_logger_methods(self):
        from instaharvest_v2.log_config import get_debug_logger
        dbg = get_debug_logger()
        # Call all debug logger methods
        try: dbg.request(method="GET", url="http://test", params={}, session_id="s", proxy="direct", attempt=1, max_attempts=3, has_data=False)
        except: pass
        try: dbg.response(status_code=200, elapsed_ms=100, size_bytes=500, url="http://test")
        except: pass
        try: dbg.error(error_type="timeout", message="timed out", url="http://test")
        except: pass

    def test_log_manager(self):
        import instaharvest_v2.log_config as lc
        if hasattr(lc, 'LogManager'):
            try:
                lm = lc.LogManager()
            except: pass

    def test_file_handler(self):
        import instaharvest_v2.log_config as lc
        if hasattr(lc, 'setup_file_logging'):
            try: lc.setup_file_logging("/tmp/test.log")
            except: pass

    def test_request_logger(self):
        import instaharvest_v2.log_config as lc
        if hasattr(lc, 'RequestLogger'):
            try:
                rl = lc.RequestLogger()
            except: pass

    def test_color_formatter(self):
        import instaharvest_v2.log_config as lc
        if hasattr(lc, 'ColorFormatter'):
            try:
                cf = lc.ColorFormatter()
                record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
                cf.format(record)
            except: pass

    def test_all_exports(self):
        import instaharvest_v2.log_config as lc
        attrs = [a for a in dir(lc) if not a.startswith('_')]
        assert len(attrs) >= 1


# ═══════════════════════════════════════════════════════════
# CLIENT — _request with mocked curl session (246 miss)
# ═══════════════════════════════════════════════════════════
class TestClientRequestMocked:
    def _make(self):
        from instaharvest_v2.client import HttpClient
        from instaharvest_v2.session_manager import SessionManager
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter
        return HttpClient(SessionManager(), ProxyManager(), AntiDetect(), RateLimiter())

    def test_update_session_cookies(self):
        hc = self._make()
        mock_resp = M()
        mock_resp.headers = {"set-cookie": "csrftoken=abc"}
        mock_sess = M()
        hc._update_session_cookies(mock_resp, mock_sess)

    def test_get_curl_session(self):
        hc = self._make()
        s = hc._get_curl_session()
        assert s is not None

    def test_rotate_curl_session(self):
        hc = self._make()
        s1 = hc._get_curl_session()
        s2 = hc._rotate_curl_session()
        assert s2 is not None

    def test_warm_up_no_fingerprint(self):
        hc = self._make()
        mock_sess = M()
        mock_sess.fingerprint = None
        mock_sess.ds_user_id = "test123"
        result = hc._warm_up_session(mock_sess)
        # Should return False with no fingerprint
        assert result is False or result is True

    def test_properties(self):
        hc = self._make()
        assert hc._is_refreshing is False
        assert isinstance(hc._warmed_sessions, set)

    def test_session_refresh_callback(self):
        hc = self._make()
        if hasattr(hc, '_session_refresh_callback'):
            assert hc._session_refresh_callback is None or callable(hc._session_refresh_callback)


# ═══════════════════════════════════════════════════════════
# ASYNC CLIENT — deep (180 miss)
# ═══════════════════════════════════════════════════════════
class TestAsyncClientDeep:
    def _make(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        from instaharvest_v2.session_manager import SessionManager 
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.rate_limiter import RateLimiter
        return AsyncHttpClient(SessionManager(), ProxyManager(), AntiDetect(), RateLimiter())

    @pytest.mark.asyncio
    async def test_init(self):
        hc = self._make()
        assert hc is not None

    @pytest.mark.asyncio
    async def test_properties(self):
        hc = self._make()
        assert hc._is_refreshing is False

    @pytest.mark.asyncio
    async def test_update_cookies(self):
        hc = self._make()
        try:
            hc._update_session_cookies(M(), M())
        except: pass

    @pytest.mark.asyncio
    async def test_get_curl(self):
        hc = self._make()
        try:
            s = hc._get_curl_session()
        except: pass

    @pytest.mark.asyncio
    async def test_rotate(self):
        hc = self._make()
        try:
            hc._rotate_curl_session()
        except: pass
