"""
Session Management
==================
Login success handling, session save/load, validation, logout,
2FA verification, and auth-related exceptions.
"""

import json
import os
import time
import logging
from typing import Any, Dict, Optional

from .constants import TWO_FACTOR_URL, WEB_USER_AGENT

logger = logging.getLogger("instaharvest_v2")


class SessionMixin:
    """Session persistence and validation methods."""

    # These attributes come from AuthAPI
    _client: Any

    @property
    def user_id(self) -> Optional[str]:
        """Get current logged-in user ID from session."""
        sess = self._client.get_session()
        if sess and hasattr(sess, 'ds_user_id') and sess.ds_user_id:
            return str(sess.ds_user_id)
        return None

    # Alias for backward compatibility
    _user_id = user_id

    def _handle_login_success(self, session, result: dict, username: str) -> Dict[str, Any]:
        """Extract and save session cookies after successful login."""
        user_id = str(result.get("userId", result.get("user_id", "")))

        cookies = {}
        for name, value in session.cookies.items():
            cookies[name] = value

        session_id = cookies.get("sessionid", "")
        csrf_token = cookies.get("csrftoken", "")
        mid = cookies.get("mid", "")
        ig_did = cookies.get("ig_did", "")
        datr = cookies.get("datr", "")
        ds_user_id = cookies.get("ds_user_id", user_id)

        if not session_id:
            raise LoginError("Login reported success, but sessionid cookie not found!")

        # Register session
        self._client._session_mgr.add_session(
            session_id=session_id,
            csrf_token=csrf_token,
            ds_user_id=ds_user_id,
            mid=mid,
            ig_did=ig_did,
            datr=datr,
            user_agent=WEB_USER_AGENT,
        )

        logger.info(f"Login successful! User: {username} (ID: {ds_user_id})")

        return {
            "status": "ok",
            "authenticated": True,
            "user_id": ds_user_id,
            "username": username,
            "session_id": session_id,
            "csrf_token": csrf_token,
        }

    def _verify_two_factor(
        self,
        session,
        username: str,
        identifier: str,
        code: str,
        csrf_token: str,
        headers: dict,
    ) -> Dict[str, Any]:
        """Verify two-factor authentication code."""
        data = {
            "username": username,
            "verificationCode": code,
            "identifier": identifier,
            "queryParams": "{}",
            "trustedDeviceRecords": "{}",
        }

        resp = session.post(
            TWO_FACTOR_URL,
            headers={**headers, "x-csrftoken": csrf_token},
            data=data,
            timeout=30,
            allow_redirects=False,
        )

        try:
            result = resp.json()
        except Exception:
            raise LoginError(f"Failed to parse 2FA response: {resp.text[:200]}")

        if result.get("authenticated"):
            return self._handle_login_success(session, result, username)

        raise LoginError(f"2FA verification failed: {result.get('message', 'Invalid code')}")

    def logout(self) -> Dict[str, Any]:
        """
        Logout from Instagram.
        Invalidates the current session.
        """
        try:
            result = self._client.post(
                "/accounts/logout/",
                data={"one_tap_app_login": "0"},
                rate_category="post_default",
            )
            logger.info("Logout successful")
            return result
        except Exception as e:
            logger.warning(f"Logout error (session may already be invalid): {e}")
            return {"status": "ok", "message": "session cleared"}

    def validate_session(self) -> bool:
        """
        Check if the current session is still valid.

        Returns:
            bool: True if session works, False if re-login needed
        """
        try:
            result = self._client.get(
                "/accounts/current_user/",
                rate_category="get_profile",
            )
            return result.get("status") == "ok" or "user" in result
        except Exception:
            return False

    def save_session(self, filepath: str) -> None:
        """
        Save current session cookies to a file.
        No re-login needed next time.

        Args:
            filepath: File path to save to (e.g. "session.json")
        """
        sess = self._client._session_mgr.get_session()
        if not sess:
            raise Exception("No active session to save!")

        data = {
            "session_id": sess.session_id,
            "csrf_token": sess.csrf_token,
            "ds_user_id": sess.ds_user_id,
            "mid": sess.mid or "",
            "ig_did": sess.ig_did or "",
            "datr": sess.datr or "",
            "user_agent": sess.user_agent or "",
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Session saved: {filepath}")

    def load_session(self, filepath: str) -> bool:
        """
        Load a previously saved session.

        Args:
            filepath: Session file path

        Returns:
            bool: True if session loaded and valid
        """
        if not os.path.exists(filepath):
            logger.warning(f"Session file not found: {filepath}")
            return False

        with open(filepath, "r") as f:
            data = json.load(f)

        self._client._session_mgr.add_session(
            session_id=data["session_id"],
            csrf_token=data["csrf_token"],
            ds_user_id=data.get("ds_user_id", data.get("user_id", "")),
            mid=data.get("mid", ""),
            ig_did=data.get("ig_did", ""),
            datr=data.get("datr", ""),
            user_agent=data.get("user_agent", ""),
            ig_www_claim=data.get("ig_www_claim", ""),
            rur=data.get("rur", ""),
        )

        is_valid = self.validate_session()
        if is_valid:
            logger.info(f"Session loaded and valid: {filepath}")
        else:
            logger.warning(f"Session loaded but invalid: {filepath}. Re-login needed.")

        return is_valid


# ─── EXCEPTIONS ──────────────────────────────────────────────

class LoginError(Exception):
    """Login error"""
    pass


class TwoFactorRequired(LoginError):
    """Two-factor authentication required"""
    pass


class CheckpointRequired(LoginError):
    """Instagram security checkpoint triggered"""
    pass
