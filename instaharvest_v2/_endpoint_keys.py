"""
Endpoint Key Normalization
==========================
Helpers for deriving stable circuit-breaker / metrics keys from URLs.

Why normalize:
    Without normalization, every unique user_id / media_pk would produce
    its own circuit breaker key. We want one breaker per logical endpoint
    so a flaky `/api/v1/users/web_profile_info/` opens its breaker
    regardless of which username triggered the failures.

    Same for metrics labels — we don't want cardinality explosion.
"""

import re
from urllib.parse import urlparse

# Numeric IDs (>=6 digits) -> <id>
_NUMERIC_ID_RE = re.compile(r"/\d{6,}(?=/|$)")
# UUID-like hex tokens (>=20 hex chars) -> <hash>
_HEX_TOKEN_RE = re.compile(r"/[A-Fa-f0-9]{20,}(?=/|$)")
# Trailing slashes
_TRAILING_SLASH_RE = re.compile(r"/+$")


def endpoint_key(url: str) -> str:
    """
    Convert a full URL into a stable endpoint identifier.

    Examples:
        https://www.instagram.com/api/v1/users/123456789/info/
            -> www.instagram.com/api/v1/users/<id>/info

        https://i.instagram.com/api/v1/feed/user/987654321/
            -> i.instagram.com/api/v1/feed/user/<id>

        https://www.instagram.com/p/ABC123def456/embed/
            -> www.instagram.com/p/ABC123def456/embed
    """
    if not url:
        return "/"
    try:
        parsed = urlparse(url)
    except Exception:
        return url[:120]

    netloc = parsed.netloc or ""
    path = parsed.path or "/"
    path = _NUMERIC_ID_RE.sub("/<id>", path)
    path = _HEX_TOKEN_RE.sub("/<hash>", path)
    path = _TRAILING_SLASH_RE.sub("", path) or "/"
    return f"{netloc}{path}"
