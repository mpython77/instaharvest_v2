"""
Auth Constants
==============
Shared constants used across auth sub-modules.
"""

# Login endpoints — wbloks/fetch (real browser uses this, NOT web_login_ajax)
WBLOKS_BASE = "https://www.instagram.com/async/wbloks/fetch/"
LOGIN_APPID = "com.bloks.www.bloks.caa.login.async.send_login_request"
AUTH_LOGIN_APPID = "com.bloks.www.bloks.caa.login.async.auth_login_request"

# Legacy endpoints (for 2FA and logout)
LOGIN_URL = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
TWO_FACTOR_URL = "https://www.instagram.com/api/v1/web/accounts/login/ajax/two_factor/"
LOGOUT_URL = "https://www.instagram.com/api/v1/web/accounts/logout/ajax/"
SHARED_DATA_URL = "https://www.instagram.com/data/shared_data/"

# Device cookies to persist (these make us a "known device")
DEVICE_COOKIES = ["mid", "ig_did", "ig_nrcb", "datr", "csrftoken"]

# Browser User-Agent (must match curl_cffi impersonation version)
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)

# Chrome version constant for sec-ch-ua headers
CHROME_VERSION = "142"
SEC_CH_UA = f'"Not A Brand";v="99", "Google Chrome";v="{CHROME_VERSION}", "Chromium";v="{CHROME_VERSION}"'
