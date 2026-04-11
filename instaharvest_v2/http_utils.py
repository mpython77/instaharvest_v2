"""
HTTP Utilities for InstaHarvest v2
===================================
Contains shared logic for synchronous and asynchronous HTTP clients to prevent code duplication.
"""

from typing import Dict, Optional, Any
from .config import IG_APP_ID, LATEST_SERVER_REVISION

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
