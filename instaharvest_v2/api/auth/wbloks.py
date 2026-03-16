"""
Wbloks Form Builder
===================
Build the wbloks/fetch form data and URL — matching real browser traffic 1:1.
"""

import time
import logging
from typing import Dict

from .constants import WBLOKS_BASE

logger = logging.getLogger("instaharvest_v2")


class WbloksMixin:
    """Wbloks form and URL building methods."""

    # Wbloks dynamic params (extracted from login page HTML)
    _wbloks_params: Dict[str, str]
    _server_revision: str

    def _build_wbloks_form(self, params_json: str, csrf_token: str) -> Dict[str, str]:
        """
        Build the complete form data for wbloks/fetch POST request.
        These params are sent with EVERY wbloks request (captured from real browser).

        Args:
            params_json: The 'params' value — already JSON-encoded inner params string
            csrf_token: Current CSRF token

        Returns:
            dict: Complete form data matching real browser 1:1
        """
        # Calculate jazoest from csrf_token (same algorithm as SessionInfo.jazoest)
        jazoest_val = "2" + str(sum(ord(c) for c in csrf_token))

        # Fallback values from captured real browser traffic
        # Instagram returns 500 if __dyn or __csr are empty!
        dyn_fallback = (
            "7xeUjG1mxu1syUbFp41twpUnwgU29zEdEc8co2qwJw5ux609vCwjE1EE2Cw8G1Qw5Mx62G3i1ywOwv89k2C1Fwc60"
            "D82Ixe0EUjwGzEaE2iwNwmE2eUlwhEe87q0oa2-azo7u3u2C2O0Lo6-3u2WE5B0bK1Iwqo5p0qZ6goK1sAwHxW1o"
            "wLwlE2xyUC4o1oE3Dw"
        )
        csr_fallback = (
            "hAIIl4OguiinblmxcBjvp2lFIiDlBAqAyf-AjDye4qnXyRVVG_-iifz4dxi-nwBgCHyogBK48aohxe6e6UliQh6xu"
            "dDyVXx6Q2nAy99bwFxq5ooGqcg888UkyFUWUWim5UydG78qyUV2HzEWUG58jy8x0jVU1jk0To01wU8eHBw1zi261"
            "qXw19Ra580ZYE0QO1hG0l20"
        )

        form = {
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": "e",
            "__hs": self._wbloks_params.get("__hs", "20511.HYP:instagram_web_pkg.2.1...0"),
            "dpr": "3",
            "__ccg": "GOOD",
            "__rev": self._wbloks_params.get("__rev", self._server_revision or "1034162388"),
            "__s": "",
            "__hsi": self._wbloks_params.get("__hsi", str(int(time.time() * 1000000))),
            "__dyn": self._wbloks_params.get("__dyn", "") or dyn_fallback,
            "__csr": self._wbloks_params.get("__csr", "") or csr_fallback,
            "__comet_req": "7",
            "lsd": self._wbloks_params.get("lsd", ""),
            "jazoest": jazoest_val,
            "__spin_r": self._wbloks_params.get("__rev", self._server_revision or "1034162388"),
            "__spin_b": self._wbloks_params.get("__spin_b", "trunk"),
            "__spin_t": self._wbloks_params.get("__spin_t", str(int(time.time()))),
            "__crn": "comet.igweb.PolarisWebBloksLoginRoute",
            "params": params_json,
        }

        return form

    def _build_wbloks_url(self, appid: str) -> str:
        """Build the wbloks/fetch URL with appid and __bkv params."""
        bkv = self._wbloks_params.get("__bkv", "")
        url = f"{WBLOKS_BASE}?appid={appid}&type=action"
        if bkv:
            url += f"&__bkv={bkv}"
        return url
