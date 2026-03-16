"""
Challenge Resolution
====================
Auto-resolve Instagram security challenges: checkpoint, auth_platform,
"This Was Me", hidden challenge probing.
"""

import json
import re
import time
import random
import logging
from typing import Any, Callable, Dict, Optional

from .constants import (
    LOGIN_URL, WEB_USER_AGENT, SEC_CH_UA,
)

logger = logging.getLogger("instaharvest_v2")


class ChallengeMixin:
    """Challenge detection and auto-resolution methods."""

    # These attributes come from AuthAPI
    _client: Any
    _server_revision: str
    _save_device_cookies: Callable
    _handle_login_success: Callable

    def _probe_for_challenge(
        self,
        session,
        csrf_token: str,
        login_headers: dict,
        login_data: dict,
    ) -> Optional[str]:
        """
        Probe for an active hidden challenge.

        When Instagram returns UserInvalidCredentials but user exists,
        there might be an unresolved challenge blocking all logins.

        Strategy:
            1. Re-send login with allow_redirects=True → check for challenge redirect
            2. Check response headers for checkpoint location
            3. Try the /challenge/ web endpoint
            4. Try /accounts/login/ and check for challenge redirect

        Returns:
            str: Challenge URL if found, None otherwise
        """
        # Strategy 1: Re-POST login with allow_redirects=True
        logger.debug("[Auth] Probe strategy 1: POST login with redirects...")
        try:
            resp = session.post(
                LOGIN_URL,
                headers=login_headers,
                data=login_data,
                timeout=30,
                allow_redirects=True,
            )

            # Check final URL for challenge
            final_url = str(resp.url) if hasattr(resp, 'url') else ""
            if "/challenge/" in final_url:
                logger.info(f"[Auth] Challenge redirect detected: {final_url}")
                return final_url

            # Check response for checkpoint_url
            try:
                data = resp.json()
                cp_url = data.get("checkpoint_url")
                if cp_url:
                    return cp_url
            except Exception:
                # HTML response — check for challenge patterns
                if "/challenge/" in resp.text:
                    match = re.search(r'(/challenge/[^"\'>\s]+)', resp.text)
                    if match:
                        return f"https://www.instagram.com{match.group(1)}"

            # Check Location header
            location = resp.headers.get("Location", resp.headers.get("location", ""))
            if "/challenge/" in location:
                return location if location.startswith("http") else f"https://www.instagram.com{location}"

        except Exception as e:
            logger.debug(f"[Auth] Probe strategy 1 failed: {e}")

        time.sleep(random.uniform(1.0, 2.0))

        # Strategy 2: Visit login page and check for challenge redirect
        logger.debug("[Auth] Probe strategy 2: GET login page with redirects...")
        try:
            resp = session.get(
                "https://www.instagram.com/accounts/login/",
                headers={
                    "user-agent": WEB_USER_AGENT,
                    "referer": "https://www.instagram.com/",
                },
                timeout=15,
                allow_redirects=True,
            )

            final_url = str(resp.url) if hasattr(resp, 'url') else ""
            if "/challenge/" in final_url:
                return final_url

            # Check HTML for challenge forms/links
            if "/challenge/" in resp.text:
                match = re.search(r'(/challenge/[^"\'>\s]+)', resp.text)
                if match:
                    return f"https://www.instagram.com{match.group(1)}"

        except Exception as e:
            logger.debug(f"[Auth] Probe strategy 2 failed: {e}")

        time.sleep(random.uniform(1.0, 2.0))

        # Strategy 3: Try the challenge API endpoint directly
        logger.debug("[Auth] Probe strategy 3: Direct /challenge/ access...")
        try:
            resp = session.get(
                "https://www.instagram.com/challenge/",
                headers={
                    "user-agent": WEB_USER_AGENT,
                    "x-csrftoken": csrf_token,
                    "referer": "https://www.instagram.com/accounts/login/",
                },
                timeout=15,
                allow_redirects=True,
            )

            final_url = str(resp.url) if hasattr(resp, 'url') else ""
            if "/challenge/" in final_url and final_url != "https://www.instagram.com/challenge/":
                return final_url

            # Check for challenge content
            if "This Was Me" in resp.text or "unusual" in resp.text.lower() or "suspicious" in resp.text.lower():
                return str(resp.url) if hasattr(resp, 'url') else "https://www.instagram.com/challenge/"

        except Exception as e:
            logger.debug(f"[Auth] Probe strategy 3 failed: {e}")

        # Strategy 4: Try Instagram's private API challenge endpoint
        logger.debug("[Auth] Probe strategy 4: Private API challenge check...")
        try:
            resp = session.get(
                "https://i.instagram.com/api/v1/challenge/",
                headers={
                    "user-agent": WEB_USER_AGENT,
                    "x-csrftoken": csrf_token,
                    "x-ig-app-id": "1217981644879628",
                },
                timeout=15,
            )

            try:
                data = resp.json()
                challenge_url = data.get("challenge", {}).get("url", "")
                if challenge_url:
                    return challenge_url
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"[Auth] Probe strategy 4 failed: {e}")

        logger.warning("[Auth] No hidden challenge found — credentials may be wrong")
        return None

    # ═══════════════════════════════════════════════════════════
    # LAYER 3: CHALLENGE AUTO-RESOLUTION
    # ═══════════════════════════════════════════════════════════

    def _resolve_checkpoint(
        self,
        session,
        checkpoint_url: str,
        csrf_token: str,
        challenge_callback: Optional[Callable] = None,
        username: str = "",
        password: str = "",
    ) -> Dict[str, Any]:
        """
        Auto-resolve a checkpoint/challenge.

        Tries:
            1. ChallengeHandler (if callback provided)
            2. "This Was Me" auto-confirm
            3. Raise CheckpointRequired as last resort
        """
        from ...challenge import ChallengeHandler, ChallengeType

        # Normalize URL
        if not checkpoint_url.startswith("http"):
            checkpoint_url = f"https://www.instagram.com{checkpoint_url}"

        # auth_platform challenges use new Instagram flow
        if "/auth_platform/" in checkpoint_url or "auth_platform" in checkpoint_url:
            logger.info("[Auth] auth_platform challenge detected")
            return self._resolve_auth_platform(
                session, checkpoint_url, csrf_token,
                challenge_callback, username, password,
            )

        # Try approach 1: GET the checkpoint page to see what type it is
        logger.info(f"[Auth] Fetching checkpoint: {checkpoint_url}")
        try:
            resp = session.get(
                checkpoint_url,
                headers={
                    "user-agent": WEB_USER_AGENT,
                    "x-csrftoken": csrf_token,
                    "referer": "https://www.instagram.com/accounts/login/",
                },
                timeout=15,
            )

            # Check if it's a "This Was Me" page
            page_text = resp.text
            if "This Was Me" in page_text or "this-was-me" in page_text or "it_was_me" in page_text:
                logger.info('[Auth] "This Was Me" challenge detected — auto-confirming...')
                # Try to auto-confirm "This Was Me"
                confirm_resp = session.post(
                    checkpoint_url,
                    headers={
                        "user-agent": WEB_USER_AGENT,
                        "x-csrftoken": csrf_token,
                        "x-requested-with": "XMLHttpRequest",
                        "referer": checkpoint_url,
                        "origin": "https://www.instagram.com",
                        "content-type": "application/x-www-form-urlencoded",
                    },
                    data={"choice": "0"},  # 0 = "This Was Me" / approve
                    timeout=15,
                )
                try:
                    confirm_result = confirm_resp.json()
                    if confirm_result.get("status") == "ok" or confirm_result.get("logged_in_user"):
                        logger.info('[Auth] "This Was Me" confirmed! ✅')
                        # Save cookies and return success
                        self._save_device_cookies(session)
                        user_id = confirm_result.get("logged_in_user", {}).get("pk", "")
                        return {
                            "status": "ok",
                            "authenticated": True,
                            "user_id": str(user_id),
                            "username": username,
                            "challenge_resolved": True,
                        }
                except Exception:
                    pass  # Fall through to ChallengeHandler

        except Exception as e:
            logger.warning(f"[Auth] Checkpoint page fetch failed: {e}")

        # Try approach 2: Use ChallengeHandler with callback
        if challenge_callback:
            logger.info("[Auth] Using ChallengeHandler to resolve...")
            handler = ChallengeHandler(code_callback=challenge_callback)
            result = handler.resolve(session, checkpoint_url, csrf_token, WEB_USER_AGENT)

            if result.success:
                logger.info("[Auth] Challenge resolved! ✅")
                self._save_device_cookies(session)
                return {
                    "status": "ok",
                    "authenticated": True,
                    "username": username,
                    "challenge_resolved": True,
                    "challenge_type": result.challenge_type.value,
                }

            logger.warning(f"[Auth] Challenge resolution failed: {result.message}")

        # Last resort: raise exception
        from .session import CheckpointRequired
        raise CheckpointRequired(
            f"Instagram security checkpoint triggered.\n"
            f"URL: {checkpoint_url}\n"
            f"Options:\n"
            f"  1. Open the URL in browser → click 'This Was Me' → retry login\n"
            f"  2. Provide challenge_callback to auto-resolve\n"
            f"  3. Wait 15-30 min and retry"
        )

    def _resolve_auth_platform(
        self,
        session,
        checkpoint_url: str,
        csrf_token: str,
        challenge_callback: Optional[Callable] = None,
        username: str = "",
        password: str = "",
    ) -> Dict[str, Any]:
        """
        Resolve auth_platform challenge using GraphQL API.
        Delegates to auth_platform module.

        After challenge resolution, re-POSTs login on the SAME session
        (a fresh self.login() would create a new session and trigger
        another challenge — infinite loop).
        """
        from ...auth_platform import resolve_auth_platform as _resolve_ap
        from .session import LoginError, TwoFactorRequired

        result = _resolve_ap(
            session, checkpoint_url, csrf_token, WEB_USER_AGENT,
            challenge_callback, username,
        )

        if result and result.get("authenticated"):
            self._save_device_cookies(session)
            return result

        # If challenge resolved but not authenticated, try to get session
        if result and result.get("challenge_resolved"):
            logger.info("[Auth] Challenge resolved — trying to complete login...")
            time.sleep(2)

            # Update CSRF token from session cookies
            new_csrf = session.cookies.get("csrftoken", csrf_token)

            # Step A: Visit Instagram homepage — browser does this after challenge
            logger.info("[Auth] Visiting instagram.com to check for session...")
            try:
                home_resp = session.get(
                    "https://www.instagram.com/",
                    headers={
                        "user-agent": WEB_USER_AGENT,
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "referer": checkpoint_url if checkpoint_url.startswith("http") else f"https://www.instagram.com{checkpoint_url}",
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "same-origin",
                    },
                    timeout=15,
                    allow_redirects=True,
                )
                logger.info(f"[Auth] Homepage status: {home_resp.status_code}, cookies: {list(session.cookies.keys())}")
            except Exception as e:
                logger.debug(f"[Auth] Homepage visit failed: {e}")

            # Check if homepage gave us session
            if session.cookies.get("sessionid"):
                logger.info("[Auth] Session cookie found after homepage visit! ✅")
                ds_user_id = session.cookies.get("ds_user_id", "")
                self._client._session_mgr.add_session(
                    session_id=session.cookies.get("sessionid", ""),
                    csrf_token=session.cookies.get("csrftoken", new_csrf),
                    ds_user_id=ds_user_id,
                    mid=session.cookies.get("mid", ""),
                    ig_did=session.cookies.get("ig_did", ""),
                    datr=session.cookies.get("datr", ""),
                    user_agent=WEB_USER_AGENT,
                )
                self._save_device_cookies(session)
                return {
                    "status": "ok",
                    "authenticated": True,
                    "user_id": ds_user_id,
                    "username": username,
                    "challenge_resolved": True,
                }

            # Step B: Re-POST login on same session
            logger.info("[Auth] No session from homepage — re-posting login...")
            enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}"

            login_headers = {
                "user-agent": WEB_USER_AGENT,
                "x-csrftoken": new_csrf,
                "x-requested-with": "XMLHttpRequest",
                "x-ig-app-id": "1217981644879628",
                "x-instagram-ajax": self._server_revision or "1033859812",
                "referer": "https://www.instagram.com/accounts/login/",
                "origin": "https://www.instagram.com",
                "content-type": "application/x-www-form-urlencoded",
                "sec-ch-ua": SEC_CH_UA,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
            }

            login_data = {
                "username": username,
                "enc_password": enc_password,
                "queryParams": "{}",
                "optIntoOneTap": "false",
                "trustedDeviceRecords": "{}",
            }

            try:
                resp = session.post(
                    LOGIN_URL,
                    headers=login_headers,
                    data=login_data,
                    timeout=30,
                    allow_redirects=True,
                )

                # Check cookies first (might have session from redirect)
                if session.cookies.get("sessionid"):
                    logger.info("[Auth] Session from re-login redirect! ✅")
                    ds_user_id = session.cookies.get("ds_user_id", "")
                    self._client._session_mgr.add_session(
                        session_id=session.cookies.get("sessionid", ""),
                        csrf_token=session.cookies.get("csrftoken", new_csrf),
                        ds_user_id=ds_user_id,
                        mid=session.cookies.get("mid", ""),
                        ig_did=session.cookies.get("ig_did", ""),
                        datr=session.cookies.get("datr", ""),
                        user_agent=WEB_USER_AGENT,
                    )
                    self._save_device_cookies(session)
                    return {
                        "status": "ok",
                        "authenticated": True,
                        "user_id": ds_user_id,
                        "username": username,
                        "challenge_resolved": True,
                    }

                try:
                    login_result = resp.json()
                except Exception:
                    logger.warning(f"[Auth] Re-login response not JSON: {resp.text[:200]}")
                    raise LoginError(f"Re-login after challenge failed: {resp.text[:200]}")

                logger.info(f"[Auth] Re-login response: {json.dumps(login_result, ensure_ascii=False)[:300]}")

                # SUCCESS
                if login_result.get("authenticated"):
                    auth_result = self._handle_login_success(session, login_result, username)
                    self._save_device_cookies(session)
                    return auth_result

                # STILL checkpoint (different type maybe)
                cp_url = login_result.get("checkpoint_url", "")
                if cp_url and "/auth_platform/" not in cp_url:
                    logger.info(f"[Auth] Different checkpoint after challenge: {cp_url}")
                    return self._resolve_checkpoint(
                        session, cp_url, new_csrf,
                        challenge_callback, username, password,
                    )

                # 2FA
                if login_result.get("two_factor_required"):
                    two_factor_info = login_result.get("two_factor_info", {})
                    identifier = two_factor_info.get("two_factor_identifier", "")
                    raise TwoFactorRequired(
                        f"Two-factor required after challenge. Identifier: {identifier}"
                    )

                logger.warning(f"[Auth] Re-login after challenge failed: {json.dumps(login_result)[:300]}")

            except (LoginError, TwoFactorRequired):
                raise
            except Exception as e:
                logger.warning(f"[Auth] Re-login POST failed: {e}")

        # Challenge failed
        if not challenge_callback:
            from .session import CheckpointRequired
            raise CheckpointRequired(
                "Email verification needed.\n"
                'Use: ig.login("user", "pass", email_credentials=("email", "app_pass"))'
            )

        from .session import LoginError as _LoginError
        raise _LoginError("auth_platform challenge could not be resolved")
