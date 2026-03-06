"""
fb_dtsg Token Provider
======================
Automatic extraction of Facebook's DTSG CSRF token from Instagram's web page.

Instagram's POST endpoints require `fb_dtsg` — a CSRF token embedded in the
HTML of instagram.com. This module fetches the page, extracts the token,
caches it with a configurable TTL, and provides it transparently to the
HTTP client layer.

Architecture:
    AsyncFbDtsgProvider
    ├── ensure_token(session)     — lazy fetch, returns cached or fresh token
    ├── fetch_from_page(session)  — HTTP GET instagram.com, parse HTML
    ├── invalidate(session)       — force re-fetch on next call
    └── _parse_html(html)         — regex extraction of all tokens

Extracted tokens:
    - fb_dtsg         — CSRF token for POST requests
    - x-ig-www-claim  — server HMAC claim (also in Set-Cookie)
    - x-instagram-ajax — build/deploy hash (rollout_hash)
"""

import re
import time
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger("instaharvest_v2.fb_dtsg")


@dataclass
class FbDtsgResult:
    """Parsed tokens from Instagram's web page."""
    fb_dtsg: str = ""
    lsd: str = ""
    rollout_hash: str = ""      # x-instagram-ajax
    claim: str = ""             # x-ig-www-claim
    device_id: str = ""         # device_id from shared data
    fetched_at: float = 0.0

    @property
    def is_valid(self) -> bool:
        return bool(self.fb_dtsg)


class AsyncFbDtsgProvider:
    """
    Automatic fb_dtsg token provider with TTL cache.

    Usage:
        provider = AsyncFbDtsgProvider(ttl_seconds=3600)

        # Before any POST request:
        await provider.ensure_token(session)
        # session.fb_dtsg is now populated

    Thread-safety:
        Uses asyncio.Lock to prevent duplicate fetches.

    Cache:
        Per-session cache with configurable TTL (default: 1 hour).
        Token is automatically re-fetched when expired.
    """

    # ─── Regex patterns for HTML extraction ─────────────────
    # Pattern 1: DTSGInitialData (modern Instagram)
    _RE_DTSG_INITIAL = re.compile(
        r'"DTSGInitialData"\s*,\s*\[\]\s*,\s*\{"token"\s*:\s*"([^"]+)"',
    )
    # Pattern 2: fb_dtsg in hidden input form
    _RE_DTSG_INPUT = re.compile(
        r'name="fb_dtsg"\s+value="([^"]+)"',
    )
    # Pattern 3: DTSGInitData in script (alternative format)
    _RE_DTSG_SCRIPT = re.compile(
        r'"DTSGInitData".*?"token":"([^"]+)"',
        re.DOTALL,
    )
    # Pattern 4: Direct token in require call
    _RE_DTSG_REQUIRE = re.compile(
        r'\["DTSGInitialData",\[\],\{"token":"([^"]+)"',
    )

    # LSD token
    _RE_LSD = re.compile(r'"LSD"\s*,\s*\[\]\s*,\s*\{"token"\s*:\s*"([^"]+)"')

    # Rollout hash / build hash (x-instagram-ajax)
    _RE_ROLLOUT = re.compile(r'"rollout_hash"\s*:\s*"([a-f0-9]+)"')
    _RE_BUILD = re.compile(r'"buildHash"\s*:\s*"([a-f0-9]+)"')

    # x-ig-www-claim from shared data
    _RE_CLAIM = re.compile(r'"claim"\s*:\s*"([^"]*)"')

    # Device ID
    _RE_DEVICE_ID = re.compile(r'"device_id"\s*:\s*"([^"]+)"')

    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: Cache TTL in seconds (default: 1 hour).
        """
        self._ttl = ttl_seconds
        self._cache: Dict[str, FbDtsgResult] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create per-session lock (non-async)."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def ensure_token(self, session, curl_session=None) -> str:
        """
        Ensure session has a valid fb_dtsg token.

        If cached and not expired → return immediately.
        If expired or missing → fetch from instagram.com.

        Args:
            session: SessionInfo instance
            curl_session: Existing curl_cffi AsyncSession to reuse

        Returns:
            fb_dtsg token string
        """
        sid = session.session_id

        # Fast path: check cache without lock
        cached = self._cache.get(sid)
        if cached and cached.is_valid and not self._is_expired(cached):
            # Token is cached and valid — update session fields
            self._apply_to_session(session, cached)
            return cached.fb_dtsg

        # Slow path: acquire per-session lock and fetch
        async with self._global_lock:
            lock = self._get_lock(sid)

        async with lock:
            # Double-check after acquiring lock
            cached = self._cache.get(sid)
            if cached and cached.is_valid and not self._is_expired(cached):
                self._apply_to_session(session, cached)
                return cached.fb_dtsg

            # Fetch from page
            logger.info("[fb_dtsg] Fetching token from instagram.com...")
            result = await self.fetch_from_page(session, curl_session=curl_session)

            if result.is_valid:
                self._cache[sid] = result
                self._apply_to_session(session, result)
                logger.info(
                    f"[fb_dtsg] ✅ Token acquired: {result.fb_dtsg[:20]}... "
                    f"| rollout={result.rollout_hash[:10] if result.rollout_hash else 'N/A'}"
                )
                return result.fb_dtsg
            else:
                logger.warning("[fb_dtsg] ⚠️ Could not extract fb_dtsg from page!")
                return ""

    async def fetch_from_page(self, session, curl_session=None) -> FbDtsgResult:
        """
        Fetch instagram.com and extract tokens from HTML.

        CRITICAL: Reuses the SAME curl_cffi session from AsyncHttpClient
        to avoid TLS fingerprint mismatch that triggers session invalidation.

        Args:
            session: SessionInfo instance
            curl_session: Existing curl_cffi AsyncSession to reuse (REQUIRED)

        Returns:
            FbDtsgResult with extracted tokens
        """
        result = FbDtsgResult(fetched_at=time.time())

        try:
            # Build web browser headers
            ua = session.user_agent
            if not ua and session.fingerprint:
                ua = session.fingerprint.user_agent
            if not ua:
                ua = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
                )

            headers = {
                "user-agent": ua,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9",
                "accept-encoding": "gzip, deflate, br",
                "cookie": session.cookie_string,
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "cache-control": "max-age=0",
            }

            # Add sec-ch-ua headers if available
            if session.fingerprint and session.fingerprint.sec_ch_ua:
                headers["sec-ch-ua"] = session.fingerprint.sec_ch_ua
                headers["sec-ch-ua-mobile"] = "?0"
                headers["sec-ch-ua-platform"] = session.fingerprint.sec_ch_ua_platform

            # Reuse existing session or create minimal fallback
            if curl_session:
                response = await curl_session.get(
                    "https://www.instagram.com/",
                    headers=headers,
                    timeout=(10, 20),
                    allow_redirects=True,
                )
            else:
                # Fallback: create session with SAME impersonate as main client
                from curl_cffi.requests import AsyncSession as CurlAsyncSession
                impersonate = "chrome142"
                if session.fingerprint:
                    impersonate = session.fingerprint.impersonate
                async with CurlAsyncSession(impersonate=impersonate) as curl:
                    response = await curl.get(
                        "https://www.instagram.com/",
                        headers=headers,
                        timeout=(10, 20),
                        allow_redirects=True,
                    )

            if response.status_code != 200:
                logger.warning(
                    f"[fb_dtsg] Page returned HTTP {response.status_code}"
                )
                return result

            html = response.text

            # Extract claim from response header
            try:
                new_claim = response.headers.get("x-ig-set-www-claim", "")
                if new_claim:
                    result.claim = new_claim
            except Exception:
                pass

            # Parse HTML
            result = self._parse_html(html, result)

            # Log page size for debugging
            logger.debug(
                f"[fb_dtsg] Page fetched: {len(html)} bytes, "
                f"tokens found: dtsg={bool(result.fb_dtsg)}"
            )

        except Exception as e:
            logger.error(f"[fb_dtsg] Fetch failed: {e}")

        return result

    def _parse_html(self, html: str, result: FbDtsgResult) -> FbDtsgResult:
        """
        Extract all tokens from Instagram's HTML page.

        Tries multiple regex patterns for resilience against
        Instagram's frequent HTML structure changes.
        """
        # ─── fb_dtsg ─────────────────────────────────────────
        for pattern in [
            self._RE_DTSG_INITIAL,
            self._RE_DTSG_REQUIRE,
            self._RE_DTSG_SCRIPT,
            self._RE_DTSG_INPUT,
        ]:
            match = pattern.search(html)
            if match:
                result.fb_dtsg = match.group(1)
                break

        # ─── LSD token ───────────────────────────────────────
        match = self._RE_LSD.search(html)
        if match:
            result.lsd = match.group(1)

        # ─── Rollout / build hash ────────────────────────────
        match = self._RE_ROLLOUT.search(html)
        if match:
            result.rollout_hash = match.group(1)
        else:
            match = self._RE_BUILD.search(html)
            if match:
                result.rollout_hash = match.group(1)

        # ─── Claim ───────────────────────────────────────────
        if not result.claim:
            match = self._RE_CLAIM.search(html)
            if match and match.group(1):
                result.claim = match.group(1)

        # ─── Device ID ──────────────────────────────────────
        match = self._RE_DEVICE_ID.search(html)
        if match:
            result.device_id = match.group(1)

        return result

    def _is_expired(self, result: FbDtsgResult) -> bool:
        """Check if cached result has exceeded TTL."""
        return (time.time() - result.fetched_at) > self._ttl

    def _apply_to_session(self, session, result: FbDtsgResult) -> None:
        """Apply extracted tokens to session object."""
        if result.fb_dtsg:
            session.fb_dtsg = result.fb_dtsg
        if result.rollout_hash and not session.x_instagram_ajax:
            session.x_instagram_ajax = result.rollout_hash
        if result.claim and not session.ig_www_claim:
            session.ig_www_claim = result.claim

    def invalidate(self, session) -> None:
        """Force re-fetch on next ensure_token() call."""
        sid = session.session_id
        if sid in self._cache:
            del self._cache[sid]
            logger.debug(f"[fb_dtsg] Cache invalidated for session {sid[:15]}...")

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        logger.debug("[fb_dtsg] All caches invalidated")
