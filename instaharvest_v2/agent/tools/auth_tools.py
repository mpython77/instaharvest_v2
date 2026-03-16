"""
Auth Tools
==========
Agent tool handlers for authentication and session management.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


def handle_login(args: Dict, ig=None, **kw) -> str:
    """Login to Instagram with username and password."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})

    try:
        username = args.get("username", "")
        password = args.get("password", "")

        if not username or not password:
            return json.dumps({"error": "Username and password are required"})

        result = ig.auth.login(username, password)
        return json.dumps({
            "status": "ok",
            "message": f"Successfully logged in as {username}",
            "user_id": result.get("user_id", ""),
        })
    except Exception as e:
        return json.dumps({"error": f"Login failed: {str(e)}"})


def handle_validate_session(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Validate current session."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Not logged in. Use login first."})

    try:
        is_valid = ig.auth.validate_session()
        return json.dumps({
            "valid": is_valid,
            "message": "Session is valid" if is_valid else "Session expired — re-login needed",
        })
    except Exception as e:
        return json.dumps({"error": f"Validation failed: {str(e)}"})


def handle_logout(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Logout from Instagram."""
    if ig is None:
        return json.dumps({"error": "Instagram instance not available"})
    if not is_logged_in:
        return json.dumps({"error": "Not logged in"})

    try:
        result = ig.auth.logout()
        return json.dumps({
            "status": "ok",
            "message": "Successfully logged out",
        })
    except Exception as e:
        return json.dumps({"error": f"Logout failed: {str(e)}"})
