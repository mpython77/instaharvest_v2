"""
Auth API Package
================
Authentication: login, session persistence, challenge resolution,
password encryption, and 2FA support.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from .session import SessionMixin, LoginError, TwoFactorRequired, CheckpointRequired
from .encryption import EncryptionMixin
from .wbloks import WbloksMixin
from .challenge import ChallengeMixin
from .constants import TWO_FACTOR_URL, LOGOUT_URL

logger = logging.getLogger("instaharvest_v2")


class AuthAPI(SessionMixin, EncryptionMixin, WbloksMixin, ChallengeMixin):
    """
    Instagram authentication API.

    Combines session management, password encryption, wbloks login form
    building, and challenge resolution into a single class.

    Usage:
        ig.auth.login("username", "password")
        ig.auth.save_session("session.json")
        ig.auth.load_session("session.json")
    """

    def __init__(self, client):
        self._client = client
        self._encryption_keys = None
        self._device_cookies_file = "device_cookies.json"
        self._server_revision = ""
        self._wbloks_params: Dict[str, str] = {
            "lsd": "",
            "__rev": "",
            "__hsi": "",
            "__dyn": "",
            "__csr": "",
            "__bkv": "",
            "__spin_b": "trunk",
            "__spin_t": "",
            "__hs": "",
        }
        self._email_credentials: Optional[Tuple[str, str]] = None

    def login(
        self,
        username: str,
        password: str,
        verification_code: Optional[str] = None,
        two_factor_callback: Optional[Callable[[], str]] = None,
        challenge_callback: Optional[Callable] = None,
        email_credentials: Optional[Tuple[str, str]] = None,
        device_cookies_file: str = "device_cookies.json",
    ) -> Dict[str, Any]:
        """
        Login to Instagram with username and password.

        Returns:
            dict with keys: status, authenticated, user_id, session_id

        Raises:
            LoginError: Login failed
            TwoFactorRequired: 2FA code needed (no callback provided)
            CheckpointRequired: Challenge could not be auto-resolved
        """
        self._email_credentials = email_credentials
        self._device_cookies_file = device_cookies_file

        try:
            enc_keys = self._get_encryption_keys()
        except Exception as e:
            logger.debug(f"[Auth] Encryption key fetch failed, proceeding without: {e}")
            enc_keys = None

        try:
            from .constants import LOGIN_URL
            result = self._client.post(
                LOGIN_URL,
                data={
                    "username": username,
                    "enc_password": self._encrypt_password(password, enc_keys) if enc_keys else f"#PWD_INSTAGRAM_BROWSER:0:0:{password}",
                    "queryParams": "{}",
                    "optIntoOneTap": "false",
                },
            )
        except Exception as e:
            raise LoginError(f"Login request failed: {e}") from e

        if not result:
            raise LoginError("Empty response from login endpoint")

        if result.get("two_factor_required"):
            if two_factor_callback:
                code = two_factor_callback()
                return self._complete_two_factor(result, code)
            raise TwoFactorRequired("Two-factor authentication required")

        if result.get("message") == "checkpoint_required" or result.get("checkpoint_url"):
            if challenge_callback:
                return self._resolve_challenge(result, challenge_callback)
            raise CheckpointRequired("Instagram security checkpoint triggered")

        if not result.get("authenticated"):
            raise LoginError(f"Login failed: {result.get('message', 'Unknown error')}")

        self._handle_login_success(
            self._client._get_curl_session(),
            result,
            username,
        )

        return {
            "status": "ok",
            "authenticated": True,
            "user_id": str(result.get("userId", result.get("user_id", ""))),
            "session_id": result.get("session_id", ""),
        }

    def logout(self) -> bool:
        """Logout from Instagram."""
        try:
            self._client.post(LOGOUT_URL, data={"one_tap_app_login": "0"})
            return True
        except Exception as e:
            logger.warning(f"[Auth] Logout error: {e}")
            return False

    def _complete_two_factor(self, login_result: Dict, code: str) -> Dict[str, Any]:
        """Complete 2FA flow with verification code."""
        two_factor_info = login_result.get("two_factor_info", {})
        identifier = two_factor_info.get("two_factor_identifier", "")
        try:
            result = self._client.post(
                TWO_FACTOR_URL,
                data={
                    "username": "",
                    "verificationCode": code,
                    "identifier": identifier,
                },
            )
            if result and result.get("authenticated"):
                return {"status": "ok", "authenticated": True}
            raise LoginError(f"2FA verification failed: {result}")
        except LoginError:
            raise
        except Exception as e:
            raise LoginError(f"2FA request failed: {e}") from e


__all__ = [
    "AuthAPI",
    "LoginError",
    "TwoFactorRequired",
    "CheckpointRequired",
]
