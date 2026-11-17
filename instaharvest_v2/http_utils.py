"""
HTTP Utilities for InstaHarvest v2
===================================
Contains shared logic for synchronous and asynchronous HTTP clients to prevent code duplication.
"""

import inspect
from typing import Dict, Optional, Any
from .config import API_BASE, BASE_URL, IG_APP_ID, LATEST_SERVER_REVISION


def normalize_api_url(endpoint: str, full_url: Optional[str] = None) -> str:
    """Resolve an API endpoint or path into a full Instagram URL without double `/api/v1`."""
    if full_url:
        return full_url
    if not endpoint:
        return API_BASE
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    if endpoint.startswith("/api/"):
        return f"{BASE_URL}{endpoint}"
    ep = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    return f"{API_BASE}{ep}"


async def maybe_await(result: Any) -> Any:
    """Await awaitable results cleanly while preserving sync-mock compatibility."""
    if inspect.isawaitable(result):
        return await result
    return result

def build_request_headers(
    method: str,
    url: str,
    sess: Any,
    anti_detect: Any,
    raw_data: Optional[bytes] = None,
    raw_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Builds and returns the standardized HTTP headers for a given request.
    Handles fingerprinted sessions vs raw identity fallbacks.
    """
    if raw_data and raw_headers:
        # Raw upload — minimal headers + fingerprint footprint
        fp = sess.fingerprint
        headers = {
            "user-agent": fp.user_agent if fp else sess.user_agent,
            "cookie": sess.cookie_string,
            "x-csrftoken": sess.csrf_token,
            "x-ig-app-id": IG_APP_ID,
            "referer": "https://www.instagram.com/",
            "origin": "https://www.instagram.com",
        }
        headers.update(raw_headers)
        return headers

    if sess.fingerprint:
        # SESSION-LOCKED HEADERS
        # All header values come from the immutable fingerprint.
        # No random rotation — Instagram sees a stable browser.
        fp = sess.fingerprint
        headers = {
            ":authority": "www.instagram.com",
            ":method": method,
            ":path": url.replace("https://www.instagram.com", ""),
            ":scheme": "https",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": sess.cookie_string,
            "origin": "https://www.instagram.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.instagram.com/",
            "sec-ch-prefers-color-scheme": "dark",
            "sec-ch-ua": fp.sec_ch_ua,
            "sec-ch-ua-full-version-list": fp.sec_ch_ua_full_version_list,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": fp.sec_ch_ua_platform,
            "sec-ch-ua-platform-version": fp.sec_ch_ua_platform_version,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": fp.user_agent,
            "x-asbd-id": "359341",
            "x-csrftoken": sess.csrf_token,
            "x-ig-app-id": IG_APP_ID,
            "x-ig-www-claim": sess.ig_www_claim or "0",
            "x-instagram-ajax": sess.x_instagram_ajax or LATEST_SERVER_REVISION,
            "x-requested-with": "XMLHttpRequest",
        }
    else:
        # Fallback — no fingerprint (should not happen for auth'd sessions)
        if method == "POST":
            headers = anti_detect.get_post_headers(sess.csrf_token)
        else:
            headers = anti_detect.get_request_headers(sess.csrf_token)

        identity = anti_detect.get_identity()
        headers["user-agent"] = identity.user_agent
        headers["sec-ch-ua"] = identity.sec_ch_ua
        headers["sec-ch-ua-mobile"] = identity.sec_ch_ua_mobile
        headers["sec-ch-ua-platform"] = identity.sec_ch_ua_platform
        if sess.ig_www_claim:
            headers["x-ig-www-claim"] = sess.ig_www_claim
        if sess.x_instagram_ajax:
            headers["x-instagram-ajax"] = sess.x_instagram_ajax
        headers.setdefault("x-asbd-id", "359341")
        headers.setdefault("sec-fetch-dest", "empty")
        headers.setdefault("sec-fetch-mode", "cors")
        headers.setdefault("sec-fetch-site", "same-origin")
        headers["cookie"] = sess.cookie_string

    return headers


def build_html_headers(
    sess: Any = None,
    authenticated: bool = True,
) -> Dict[str, str]:
    """Build coherent browser navigation headers for fetching raw Instagram HTML."""
    fp = getattr(sess, "fingerprint", None) if sess else None
    ua = (
        (fp.user_agent if fp else getattr(sess, "user_agent", ""))
        or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    )
    headers: Dict[str, str] = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": ua,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none" if not authenticated else "same-origin",
    }
    if authenticated and sess and getattr(sess, "cookie_string", ""):
        headers["cookie"] = sess.cookie_string
    return headers
