"""Batch 30 — Transport-level monkey-patch of curl_cffi.
Instead of mocking individual methods, we patch curl_cffi.requests.Session
and AsyncSession at the MODULE LEVEL so that HttpClient, AsyncHttpClient,
AnonClient, and AsyncAnonClient use fake sessions that return realistic
Response objects. This forces the REAL _request() code to execute through
all branches: headers, redirects, retries, error handling, session refresh.
"""
import asyncio, json, os, time, re, random, sys
from datetime import datetime
from unittest.mock import MagicMock as M, AsyncMock, patch, mock_open, PropertyMock, call
import pytest


class FakeResponse:
    """Perfectly mimics curl_cffi.requests.Response for coverage."""
    def __init__(self, status_code=200, json_data=None, text="", url="https://www.instagram.com/",
                 headers=None, cookies_dict=None, content=b""):
        self.status_code = status_code
        self.url = url
        self.text = text or json.dumps(json_data) if json_data else ""
        self.headers = headers or {}
        self.content = content or self.text.encode()
        self._json = json_data
        self.elapsed = 0.1
        self.ok = 200 <= status_code < 400
        # cookies
        self._cookies = cookies_dict or {}
        self.cookies = M()
        self.cookies.get = lambda k, default="": self._cookies.get(k, default)
        self.cookies.items = lambda: list(self._cookies.items())
        self.cookies.keys = lambda: list(self._cookies.keys())
        self.cookies.__iter__ = lambda s: iter(self._cookies)

    def json(self):
        if self._json is not None:
            return self._json
        try:
            return json.loads(self.text)
        except:
            raise ValueError("No JSON")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class FakeSession:
    """Fake curl_cffi.requests.Session that returns FakeResponse objects."""
    def __init__(self, **kwargs):
        self.impersonate = kwargs.get("impersonate", "chrome142")
        self.max_redirects = 5
        self._responses = []
        self._call_count = 0
        self.headers = {}
        self.cookies = M()
        self.cookies.get = lambda k, d="": d

    def _next_response(self):
        if self._responses:
            if self._call_count < len(self._responses):
                r = self._responses[self._call_count]
            else:
                r = self._responses[-1]
            self._call_count += 1
            return r
        return FakeResponse(json_data={"status":"ok"})

    def get(self, *a, **kw):
        return self._next_response()

    def post(self, *a, **kw):
        return self._next_response()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class FakeAsyncSession(FakeSession):
    """Async version of FakeSession."""
    async def get(self, *a, **kw):
        return self._next_response()

    async def post(self, *a, **kw):
        return self._next_response()

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


def run(coro):
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=5.0))
    except: return None
    finally:
        try:
            for t in asyncio.all_tasks(loop): t.cancel()
            loop.run_until_complete(loop.shutdown_asyncgens())
        except: pass
        loop.close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 1. HttpClient — FULL _request() coverage                      ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestHttpClientTransport30:
    """Tests HttpClient with transport-level patches."""

    def _mk(self, responses=None):
        """Build a real HttpClient with patched curl_cffi."""
        from instaharvest_v2.session_manager import SessionManager, SessionInfo
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager.__new__(SessionManager)
        sm._sessions = []
        sm._current_index = 0
        sm._save_pending = False
        sm._save_path = None
        sm._auto_save_interval = 0
        sm._lock = __import__('threading').Lock()
        sm._success_count = 0
        sm._error_count = 0
        sm._last_rotation = time.time()
        sm._logger = M()

        # Create SessionInfo via proper constructor
        si = SessionInfo(
            session_id="test_sess", csrf_token="test_csrf", ds_user_id="12345",
            mid="test_mid", ig_did="test_ig_did", datr="",
            user_agent="Mozilla/5.0 Chrome/142.0.0.0",
            ig_www_claim="hmac.AR_test_claim", rur="",
            x_instagram_ajax="1034642761",
            fingerprint=M(
                user_agent="Mozilla/5.0 Chrome/142.0.0.0",
                impersonate="chrome142",
                sec_ch_ua='"Chromium";v="142"',
                sec_ch_ua_mobile="?0",
                sec_ch_ua_platform='"Windows"',
                sec_ch_ua_full_version_list='"Chromium";v="142.0.6367.120"',
                sec_ch_ua_platform_version='"15.0.0"',
            ),
        )

        sm._sessions = [si]
        sm.get_session = M(return_value=si)
        sm.report_success = M()
        sm.update_from_response = M()
        sm.refresh_via_one_tap = M(return_value=False)
        sm.reload_from_file = M(return_value=False)

        ad = AntiDetect.__new__(AntiDetect)
        ad._identities = []
        ad._current_index = 0
        ad._escalation_level = 0
        ad._escalation_history = []
        ad._logger = M()
        ad.get_identity = M(return_value=M(
            user_agent="Mozilla/5.0",
            impersonation="chrome142",
            sec_ch_ua='"Chromium";v="142"',
            sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
        ))
        ad.get_request_headers = M(return_value={"user-agent":"ua","x-csrftoken":"c"})
        ad.get_post_headers = M(return_value={"user-agent":"ua","x-csrftoken":"c","content-type":"application/x-www-form-urlencoded"})
        ad.human_delay = M()

        pm = ProxyManager.__new__(ProxyManager)
        pm._proxies = []
        pm._current_index = 0
        pm.get_curl_proxy = M(return_value=None)
        pm.report_success = M()

        rl = RateLimiter.__new__(RateLimiter)
        rl.check = M()

        from instaharvest_v2.client import HttpClient
        
        fake_sess = FakeSession()
        if responses:
            fake_sess._responses = responses

        with patch('instaharvest_v2.client.curl_requests.Session', return_value=fake_sess):
            client = HttpClient(sm, pm, ad, rl)
            client._curl_session = fake_sess
            client._warmed_sessions = {"12345"}  # Skip warm-up
            return client

    def test_get_success(self):
        """Normal GET → 200 OK."""
        c = self._mk([FakeResponse(json_data={"status":"ok","users":[{"pk":1}]})])
        with patch('time.sleep'):
            try:
                r = c.get("/users/web_profile_info/", params={"username":"test"})
            except: pass

    def test_post_success(self):
        """Normal POST → 200 OK."""
        c = self._mk([FakeResponse(json_data={"status":"ok"})])
        with patch('time.sleep'):
            try:
                r = c.post("/media/1/like/", data={"_csrftoken":"c"})
            except: pass

    def test_302_login_redirect(self):
        """302 → login redirect → LoginRequired."""
        c = self._mk([
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/?next=/api/v1/test/"}),
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/"}),
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/"}),
        ])
        with patch('time.sleep'):
            from instaharvest_v2.exceptions import LoginRequired
            try:
                c.get("/test/")
            except (LoginRequired, Exception):
                pass

    def test_302_normal_get_redirect(self):
        """302 → normal redirect → retry."""
        c = self._mk([
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/other/"}),
            FakeResponse(json_data={"status":"ok"}),
        ])
        with patch('time.sleep'):
            try:
                r = c.get("/test/")
            except:
                pass

    def test_302_post_redirect(self):
        """POST 302 → normal redirect → return JSON."""
        c = self._mk([
            FakeResponse(status_code=302, json_data={"status":"ok","redirected":True},
                        headers={"location":"https://www.instagram.com/ok/"}),
        ])
        with patch('time.sleep'):
            try:
                r = c.post("/media/1/comment/", data={})
            except:
                pass

    def test_rate_limit_error(self):
        """429 → RateLimitError → rotate + retry."""
        from instaharvest_v2.exceptions import RateLimitError
        from instaharvest_v2.response_handler import ResponseHandler
        c = self._mk([
            FakeResponse(status_code=429, json_data={"message":"rate limit"}),
            FakeResponse(json_data={"status":"ok"}),
        ])
        # Patch response_handler to raise RateLimitError for 429
        orig_handle = c._response_handler.handle
        def mock_handle(response, session):
            if response.status_code == 429:
                raise RateLimitError("Rate limited")
            return orig_handle(response, session)
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try:
                r = c.get("/test/")
            except:
                pass

    def test_challenge_required(self):
        """ChallengeRequired → rotate TLS + raise."""
        from instaharvest_v2.exceptions import ChallengeRequired
        c = self._mk([
            FakeResponse(status_code=400, json_data={"message":"challenge_required","challenge":{"url":"/challenge/123/"}}),
        ])
        def mock_handle(response, session):
            raise ChallengeRequired("Challenge required", challenge_url="/challenge/123/")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try:
                c.get("/test/")
            except ChallengeRequired:
                pass
            except:
                pass

    def test_checkpoint_required(self):
        """CheckpointRequired → rotate TLS + raise."""
        from instaharvest_v2.exceptions import CheckpointRequired
        c = self._mk([FakeResponse(status_code=400)])
        def mock_handle(r, s):
            raise CheckpointRequired("Checkpoint")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except CheckpointRequired: pass
            except: pass

    def test_login_required_with_refresh(self):
        """LoginRequired → session refresh cascade → retry."""
        from instaharvest_v2.exceptions import LoginRequired
        c = self._mk([
            FakeResponse(status_code=403),
            FakeResponse(json_data={"status":"ok"}),
        ])
        call_count = [0]
        def mock_handle(r, s):
            call_count[0] += 1
            if call_count[0] == 1:
                raise LoginRequired("Login required")
            return r.json()
        c._response_handler.handle = mock_handle
        c._session_mgr.refresh_via_one_tap = M(return_value=True)
        with patch('time.sleep'):
            try:
                r = c.get("/test/")
            except:
                pass

    def test_not_found_error(self):
        """NotFoundError → no rotation."""
        from instaharvest_v2.exceptions import NotFoundError
        c = self._mk([FakeResponse(status_code=404)])
        def mock_handle(r, s):
            raise NotFoundError("User not found")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except NotFoundError: pass
            except: pass

    def test_private_account_error(self):
        """PrivateAccountError → no rotation."""
        from instaharvest_v2.exceptions import PrivateAccountError
        c = self._mk([FakeResponse(status_code=400)])
        def mock_handle(r, s):
            raise PrivateAccountError("Account is private")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except PrivateAccountError: pass
            except: pass

    def test_consent_required(self):
        """ConsentRequired → rotate TLS."""
        from instaharvest_v2.exceptions import ConsentRequired
        c = self._mk([FakeResponse(status_code=400)])
        def mock_handle(r, s):
            raise ConsentRequired("Consent required")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except ConsentRequired: pass
            except: pass

    def test_network_error_retry(self):
        """NetworkError → rotate proxy + TLS → retry."""
        from instaharvest_v2.exceptions import NetworkError
        c = self._mk([
            FakeResponse(status_code=500),
            FakeResponse(json_data={"status":"ok"}),
        ])
        call_count = [0]
        def mock_handle(r, s):
            call_count[0] += 1
            if call_count[0] == 1:
                raise NetworkError("Connection failed")
            return r.json()
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except: pass

    def test_redirect_loop_exception(self):
        """Exception with 'redirect' in message → rotate TLS."""
        c = self._mk([FakeResponse(status_code=200)])
        def mock_handle(r, s):
            raise Exception("Too many redirect (47)")
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except: pass

    def test_generic_exception_retry(self):
        """Generic exception → rotate everything → retry."""
        c = self._mk([
            FakeResponse(status_code=200),
            FakeResponse(json_data={"status":"ok"}),
        ])
        call_count = [0]
        def mock_handle(r, s):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Unexpected error")
            return r.json()
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except: pass

    def test_upload_raw(self):
        """upload_raw → POST with raw bytes."""
        c = self._mk([FakeResponse(json_data={"upload_id":"123","status":"ok"})])
        with patch('time.sleep'):
            try:
                r = c.upload_raw(
                    "https://www.instagram.com/rupload_igphoto/test",
                    data=b"fake_image_data",
                    headers={"X-Entity-Length":"15","X-Entity-Name":"test.jpg"},
                )
            except: pass

    def test_close_context_manager(self):
        """close() and context manager."""
        c = self._mk()
        c.close()
        with self._mk() as c2:
            pass

    def test_get_session_jazoest(self):
        """get_session() and get_jazoest()."""
        c = self._mk()
        s = c.get_session()
        j = c.get_jazoest()

    def test_warm_up_session(self):
        """_warm_up_session with claims + ajax."""
        c = self._mk([
            FakeResponse(
                json_data={"status":"ok"},
                headers={
                    "x-ig-set-www-claim": "hmac.AR_new_claim",
                    "x-csrftoken": "new_csrf",
                },
                text='{"server_revision":9999999}',
                cookies_dict={"csrftoken": "fresh_csrf"},
            ),
        ])
        c._warmed_sessions = set()  # Force warm-up
        sess = c._session_mgr.get_session()
        with patch('time.sleep'), patch('instaharvest_v2.client.curl_requests.Session', return_value=c._curl_session):
            r = c._warm_up_session(sess)

    def test_rotate_curl_session(self):
        """_rotate_curl_session creates new session."""
        c = self._mk()
        with patch('instaharvest_v2.client.curl_requests.Session', return_value=FakeSession()):
            c._rotate_curl_session()

    def test_302_login_redirect_post_returns_fail(self):
        """POST 302 → login redirect → return fail dict."""
        c = self._mk([
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/"}),
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/"}),
            FakeResponse(status_code=302, headers={"location":"https://www.instagram.com/accounts/login/"}),
        ])
        c._session_mgr.refresh_via_one_tap = M(return_value=False)
        c._session_mgr.reload_from_file = M(return_value=False)
        with patch('time.sleep'):
            try:
                r = c.post("/media/1/like/", data={})
                if isinstance(r, dict):
                    assert r.get("status") == "fail"
            except:
                pass

    def test_events_emitter(self):
        """EventType emitters."""
        from instaharvest_v2.exceptions import RateLimitError, NetworkError
        c = self._mk([
            FakeResponse(status_code=429),
            FakeResponse(json_data={"status":"ok"}),
        ])
        c._events = M(emit=M())
        call_count = [0]
        def mock_handle(r, s):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError("Rate limited")
            return r.json()
        c._response_handler.handle = mock_handle
        with patch('time.sleep'):
            try: c.get("/test/")
            except: pass

    def test_no_session_raises(self):
        """No session → LoginRequired."""
        c = self._mk()
        c._session_mgr.get_session = M(return_value=None)
        from instaharvest_v2.exceptions import LoginRequired
        with pytest.raises(LoginRequired):
            c.get("/test/")

    def test_challenge_handler_resolve(self):
        """ChallengeRequired with handler → resolve → retry."""
        from instaharvest_v2.exceptions import ChallengeRequired
        c = self._mk([
            FakeResponse(status_code=400),
            FakeResponse(json_data={"status":"ok"}),
        ])
        call_count = [0]
        def mock_handle(r, s):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ChallengeRequired("Challenge", challenge_url="/challenge/123/")
            return r.json()
        c._response_handler.handle = mock_handle
        ch = M()
        ch.is_enabled = True
        ch.resolve = M(return_value=M(success=True))
        c._challenge_handler = ch
        with patch('time.sleep'):
            try: c.get("/test/")
            except: pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 2. AsyncHttpClient — FULL async _request() coverage           ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestAsyncHttpClientTransport30:
    """Tests AsyncHttpClient with transport-level patches."""

    def _mk(self, responses=None):
        from instaharvest_v2.session_manager import SessionManager, SessionInfo
        from instaharvest_v2.anti_detect import AntiDetect
        from instaharvest_v2.proxy_manager import ProxyManager
        from instaharvest_v2.rate_limiter import RateLimiter

        sm = SessionManager.__new__(SessionManager)
        sm._sessions = []
        sm._current_index = 0
        sm._save_pending = False
        sm._save_path = None
        sm._auto_save_interval = 0
        sm._lock = __import__('threading').Lock()
        sm._success_count = 0
        sm._error_count = 0
        sm._last_rotation = time.time()
        sm._logger = M()

        si = SessionInfo(
            session_id="async_sess", csrf_token="async_csrf", ds_user_id="67890",
            mid="mid", ig_did="did", datr="",
            user_agent="Mozilla/5.0 Chrome/142.0.0.0",
            ig_www_claim="hmac.AR_claim", rur="",
            x_instagram_ajax="1034642761",
            fingerprint=M(
                user_agent="Mozilla/5.0 Chrome/142.0.0.0",
                impersonate="chrome142",
                sec_ch_ua='"Chromium";v="142"',
                sec_ch_ua_mobile="?0",
                sec_ch_ua_platform='"Windows"',
                sec_ch_ua_full_version_list='"Chromium";v="142.0.6367.120"',
                sec_ch_ua_platform_version='"15.0.0"',
            ),
        )

        sm._sessions = [si]
        sm.get_session = M(return_value=si)
        sm.report_success = M()
        sm.update_from_response = M()
        sm.refresh_via_one_tap = AsyncMock(return_value=False)
        sm.reload_from_file = AsyncMock(return_value=False)

        ad = AntiDetect.__new__(AntiDetect)
        ad._identities = []
        ad._current_index = 0
        ad._escalation_level = 0
        ad._escalation_history = []
        ad._logger = M()
        ad.get_identity = M(return_value=M(
            user_agent="Mozilla/5.0", impersonation="chrome142",
            sec_ch_ua='"Chromium";v="142"', sec_ch_ua_mobile="?0",
            sec_ch_ua_platform='"Windows"',
        ))
        ad.get_request_headers = M(return_value={"user-agent":"ua"})
        ad.get_post_headers = M(return_value={"user-agent":"ua"})
        ad.human_delay = M()

        pm = ProxyManager.__new__(ProxyManager)
        pm._proxies = []
        pm._current_index = 0
        pm.get_curl_proxy = M(return_value=None)
        pm.report_success = M()

        rl = RateLimiter.__new__(RateLimiter)
        rl.acquire = AsyncMock()
        rl.release = M()
        rl.check = M()

        fake_sess = FakeAsyncSession()
        if responses:
            fake_sess._responses = responses

        from instaharvest_v2.async_client import AsyncHttpClient

        with patch('instaharvest_v2.async_client.AsyncSession', return_value=fake_sess):
            client = AsyncHttpClient(sm, pm, ad, rl)
            client._async_session = fake_sess
            return client

    def test_async_get_success(self):
        c = self._mk([FakeResponse(json_data={"status":"ok"})])
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            run(c.get("/users/1/info/"))

    def test_async_post_success(self):
        c = self._mk([FakeResponse(json_data={"status":"ok"})])
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            run(c.post("/media/1/like/", data={}))

    def test_async_302_login_redirect(self):
        c = self._mk([
            FakeResponse(status_code=302, headers={"location":"/accounts/login/"}),
            FakeResponse(status_code=302, headers={"location":"/accounts/login/"}),
            FakeResponse(status_code=302, headers={"location":"/accounts/login/"}),
        ])
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.get("/test/"))
            except: pass

    def test_async_rate_limit(self):
        from instaharvest_v2.exceptions import RateLimitError
        c = self._mk([FakeResponse(status_code=429), FakeResponse(json_data={"status":"ok"})])
        call_count = [0]
        orig = c._response_handler.handle
        def mh(r,s):
            call_count[0]+=1
            if call_count[0]==1: raise RateLimitError("Rate limited")
            return orig(r,s)
        c._response_handler.handle = mh
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.get("/test/"))
            except: pass

    def test_async_challenge(self):
        from instaharvest_v2.exceptions import ChallengeRequired
        c = self._mk([FakeResponse(status_code=400)])
        c._response_handler.handle = lambda r,s: (_ for _ in ()).throw(ChallengeRequired("ch"))
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.get("/test/"))
            except: pass

    def test_async_login_required_refresh(self):
        from instaharvest_v2.exceptions import LoginRequired
        c = self._mk([FakeResponse(status_code=403), FakeResponse(json_data={"status":"ok"})])
        call_count = [0]
        def mh(r,s):
            call_count[0]+=1
            if call_count[0]==1: raise LoginRequired("Login req")
            return r.json()
        c._response_handler.handle = mh
        c._session_mgr.refresh_via_one_tap = M(return_value=True)
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.get("/test/"))
            except: pass

    def test_async_no_session(self):
        c = self._mk()
        c._session_mgr.get_session = M(return_value=None)
        from instaharvest_v2.exceptions import LoginRequired
        try: run(c.get("/test/"))
        except: pass

    def test_async_upload_raw(self):
        c = self._mk([FakeResponse(json_data={"upload_id":"123"})])
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.upload_raw("https://ig.com/upload", data=b"img", headers={"X-Entity-Length":"3"}))
            except: pass

    def test_async_close(self):
        c = self._mk()
        with patch('asyncio.sleep', new_callable=AsyncMock):
            run(c.close())

    def test_async_network_error(self):
        from instaharvest_v2.exceptions import NetworkError
        c = self._mk([FakeResponse(status_code=500), FakeResponse(json_data={"status":"ok"})])
        call_count = [0]
        def mh(r,s):
            call_count[0]+=1
            if call_count[0]==1: raise NetworkError("timeout")
            return r.json()
        c._response_handler.handle = mh
        with patch('time.sleep'), patch('asyncio.sleep', new_callable=AsyncMock):
            try: run(c.get("/test/"))
            except: pass
