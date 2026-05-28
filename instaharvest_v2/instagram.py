"""
Instagram - Main Class
=======================
Main class that unifies all API modules.
Simple and powerful interface.

Architecture:
    Core components (HttpClient, SessionManager, ProxyManager, etc.) are
    instantiated eagerly in __init__ because they are foundational.

    The 30+ API modules (users, media, feed, ...) are lazy-loaded via
    __getattr__ — they are imported and constructed only on first access.
    See _lazy_modules.py for the registry.
"""

import logging
from typing import Any, List, Optional

from .client import HttpClient
from .session_manager import SessionManager
from .proxy_manager import ProxyManager, RotationStrategy
from .anti_detect import AntiDetect
from .rate_limiter import RateLimiter
from .challenge import ChallengeHandler
from .retry import RetryConfig
from .log_config import LogConfig, DebugLogger, set_debug_logger, get_debug_logger
from .events import EventEmitter, EventType, EventData
from .dashboard import Dashboard
from .plugin import Plugin, PluginManager
from .proxy_health import ProxyHealthChecker
from .story_composer import StoryComposer
from .anon_client import AnonClient
from ._lazy_modules import LAZY_API_MODULES, LAZY_MODULE_NAMES

# Re-exports kept for backward compatibility (referenced by callers as
# `from instaharvest_v2.instagram import ExportFilter` etc.). They are
# imported lazily through __getattr__ at the module level if needed.
# Direct importers should switch to `from instaharvest_v2 import ...`.
from .api.export import ExportFilter
from .api.scheduler import SchedulerJob
from .api.growth import GrowthFilters, GrowthLimits
from .api.automation import AutomationLimits, TemplateEngine
from .api.monitor import AccountWatcher

logger = logging.getLogger("instaharvest_v2")


class Instagram:
    """
    Instagram Private API — main class.

    Basic usage (with cookies):
        ig = Instagram.from_env('.env')
        user = ig.users.get_by_username('cristiano')

    Login with credentials:
        ig = Instagram()
        ig.login('username', 'password')
        ig.auth.save_session('session.json')  # save session

    Load saved session:
        ig = Instagram()
        ig.auth.load_session('session.json')  # no re-login needed

    With proxy:
        ig = Instagram.from_env('.env')
        ig.add_proxies(['socks5://ip:port', 'http://user:pass@ip:port'])

    With multiple accounts:
        ig = Instagram.from_env('.env')  # SESSION_ID_2, SESSION_ID_3, ... in .env

    Anonymous (no login):
        ig = Instagram.anonymous()
        profile = ig.public.get_profile('cristiano')
        posts = ig.public.get_posts('cristiano')
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        csrf_token: Optional[str] = None,
        ds_user_id: Optional[str] = None,
        mid: str = "",
        ig_did: str = "",
        datr: str = "",
        user_agent: str = "",
        ig_www_claim: str = "",
        rur: str = "",
        x_instagram_ajax: str = "",
        username: str = "",
        password: str = "",
        rate_limiting: bool = True,
        challenge_callback=None,
        session_file: Optional[str] = None,
        retry: Optional[RetryConfig] = None,
        log_level: str = "WARNING",
        log_file: Optional[str] = None,
        log_format: Optional[str] = None,
        debug: bool = False,
        debug_log_file: Optional[str] = None,
    ):
        """
        Create Instagram API client.

        Args:
            session_id: Instagram session cookie
            csrf_token: CSRF token
            ds_user_id: User ID
            mid, ig_did, datr: Optional cookies
            user_agent: User-Agent (optional)
            ig_www_claim: x-ig-www-claim HMAC header
            rur: rur cookie value
            x_instagram_ajax: x-instagram-ajax build hash
            username: Instagram username (for auto re-login)
            password: Instagram password (for auto re-login)
            rate_limiting: Enable/disable rate limiting
            challenge_callback: Callback for challenge code input
            session_file: Path to session JSON for auto-save
            retry: RetryConfig instance for custom retry/backoff
            log_level: Logging level (DEBUG/INFO/WARNING/ERROR)
            log_file: Log file path (None = console only)
            log_format: Custom log format string
            debug: Enable structured debug logging (emoji-coded output)
            debug_log_file: Debug log file path (None = console only)
        """
        # ─── DEBUG MODE ──────────────────────────────────────
        if debug:
            self._debug = DebugLogger(enabled=True, log_file=debug_log_file)
            set_debug_logger(self._debug)
            log_level = "DEBUG"  # Force DEBUG level
        else:
            self._debug = DebugLogger(enabled=False)

        # Auto re-login credentials
        self._username = username
        self._password = password
        # Logging
        LogConfig.configure(
            level=log_level,
            filename=log_file,
            format=log_format,
        )

        # Core components
        self._session_mgr = SessionManager(
            auto_save_path=session_file,
            auto_save_interval=20,
        )
        self._proxy_mgr = ProxyManager(strategy=RotationStrategy.WEIGHTED)
        self._anti_detect = AntiDetect()
        self._rate_limiter = RateLimiter(enabled=rate_limiting)
        self._challenge_handler = ChallengeHandler(
            code_callback=challenge_callback,
        )
        self._session_file = session_file
        self._retry = retry or RetryConfig()
        self._events = EventEmitter()

        # Add session if credentials provided
        if session_id and csrf_token and ds_user_id:
            self._session_mgr.add_session(
                session_id=session_id,
                csrf_token=csrf_token,
                ds_user_id=ds_user_id,
                mid=mid,
                ig_did=ig_did,
                datr=datr,
                user_agent=user_agent,
                ig_www_claim=ig_www_claim,
                rur=rur,
                x_instagram_ajax=x_instagram_ajax,
            )

        # HTTP client
        self._client = HttpClient(
            session_manager=self._session_mgr,
            proxy_manager=self._proxy_mgr,
            anti_detect=self._anti_detect,
            rate_limiter=self._rate_limiter,
            challenge_handler=self._challenge_handler,
            session_refresh_callback=self._build_refresh_callback(),
            retry_config=self._retry,
            event_emitter=self._events,
        )

        # API modules are lazy-loaded via __getattr__ — see _lazy_modules.py.
        # Only the underlying _client and _anon_client are eager because
        # other components depend on them.

        # Anonymous public API (no login needed)
        # If user has a session, pass cookies to AnonClient for better data access
        anon_cookies = None
        if session_id and ds_user_id:
            anon_cookies = {
                "sessionid": session_id,
                "ds_user_id": ds_user_id,
            }
            if csrf_token:
                anon_cookies["csrftoken"] = csrf_token
            if mid:
                anon_cookies["mid"] = mid
            if ig_did:
                anon_cookies["ig_did"] = ig_did
            if datr:
                anon_cookies["datr"] = datr

        self._anon_client = AnonClient(
            anti_detect=self._anti_detect,
            proxy_manager=self._proxy_mgr,
            cookies=anon_cookies,
        )

        # Dashboard + Plugin manager
        self.dashboard = Dashboard(
            rate_limiter=self._rate_limiter,
            proxy_manager=self._proxy_mgr,
            session_manager=self._session_mgr,
            event_emitter=self._events,
        )
        self._plugin_mgr = PluginManager(event_emitter=self._events)
        self._proxy_health: Optional[ProxyHealthChecker] = None

    # ─── LAZY API MODULE LOADING ─────────────────────────────

    def __getattr__(self, name: str) -> Any:
        """
        Lazy attribute lookup for API modules.

        Called by Python only when normal lookup fails — i.e., for any
        attribute not yet present in self.__dict__ or on the class.

        For names listed in LAZY_API_MODULES we instantiate the module
        on demand, cache it in self.__dict__ (so the next lookup hits
        the fast path and never calls __getattr__ again), and return it.

        Inter-module dependencies (e.g., feed -> graphql) resolve naturally:
        the factory accesses self.graphql, which triggers another
        __getattr__ call if needed.
        """
        # Avoid recursion during early construction (before _client is set)
        if name.startswith("_"):
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {name!r}"
            )

        factory = LAZY_API_MODULES.get(name)
        if factory is None:
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {name!r}"
            )

        try:
            module = factory(self)
        except Exception as exc:
            # Wrap the original error so the user sees which module failed
            raise AttributeError(
                f"Failed to load API module {name!r}: {type(exc).__name__}: {exc}"
            ) from exc

        # Cache on the instance — future accesses bypass __getattr__
        self.__dict__[name] = module
        return module

    def __dir__(self) -> List[str]:
        """Include lazy-loaded API modules in dir() output."""
        return sorted(set(super().__dir__()) | set(LAZY_MODULE_NAMES))

    @property
    def loaded_modules(self) -> List[str]:
        """Return names of API modules currently loaded (already accessed)."""
        return [name for name in LAZY_MODULE_NAMES if name in self.__dict__]

    def _build_refresh_callback(self):
        """
        Auto session refresh callback.

        Called by HttpClient when a 302 login redirect occurs.
        3-step cascade:
        1. one_tap_web_login  — no password needed, uses existing cookies
        2. reload_from_file   — picks up externally updated session
        3. full re-login      — uses stored credentials (last resort)

        Returns:
            Callable: refresh function (always returns a callback)
        """

        def _do_refresh() -> bool:
            session = self._session_mgr.get_session()
            if not session:
                logger.warning("[Session Refresh] No active session to refresh.")
                return False

            # Step 1: one_tap_web_login (preferred — no password needed)
            try:
                logger.info("[Session Refresh] Step 1: one_tap_web_login...")
                if self._session_mgr.refresh_via_one_tap(session):
                    logger.info("✅ [Session Refresh] one_tap success!")
                    return True
            except Exception as e:
                logger.warning(f"[Session Refresh] one_tap error: {e}")

            # Step 2: reload from file
            try:
                logger.info("[Session Refresh] Step 2: reload_from_file...")
                if self._session_mgr.reload_from_file(session):
                    logger.info("✅ [Session Refresh] file reload success!")
                    return True
            except Exception as e:
                logger.warning(f"[Session Refresh] file reload error: {e}")

            # Step 3: full re-login (only if credentials available)
            if self._username and self._password:
                try:
                    logger.info(
                        f"[Session Refresh] Step 3: Re-login as @{self._username}..."
                    )
                    result = self.auth.login(
                        username=self._username,
                        password=self._password,
                    )
                    if result and result.get("authenticated"):
                        logger.info("✅ [Session Refresh] Re-login success!")
                        if self._session_file:
                            self.auth.save_session(self._session_file)
                        return True
                    else:
                        logger.error(f"[Session Refresh] Re-login failed: {result}")
                except Exception as e:
                    logger.error(f"[Session Refresh] Re-login error: {e}")

            logger.error("[Session Refresh] All 3 steps failed.")
            return False

        return _do_refresh

    # ─── EVENT SYSTEM ────────────────────────────────────────

    def on(self, event_type, callback):
        """Register event listener. See EventType for available events."""
        self._events.on(event_type, callback)
        return self

    def off(self, event_type, callback):
        """Remove event listener."""
        self._events.off(event_type, callback)
        return self

    # ─── PLUGIN SYSTEM ───────────────────────────────────────

    def use(self, plugin) -> "Instagram":
        """Install a plugin. See Plugin base class."""
        self._plugin_mgr.install(plugin, self)
        return self

    def remove_plugin(self, name: str) -> bool:
        """Remove a plugin by name."""
        return self._plugin_mgr.uninstall(name)

    # ─── PROXY HEALTH ────────────────────────────────────────

    def start_proxy_health(self, interval: float = 300) -> None:
        """Start background proxy health checker."""
        if not self._proxy_health:
            self._proxy_health = ProxyHealthChecker(
                self._proxy_mgr, interval=interval, event_emitter=self._events,
            )
        self._proxy_health.start()

    def stop_proxy_health(self) -> None:
        """Stop proxy health checker."""
        if self._proxy_health:
            self._proxy_health.stop()

    # ─── STORY COMPOSER ──────────────────────────────────────

    def compose_story(self) -> "StoryComposer":
        """Create a new story builder. Returns StoryComposer(self)."""
        return StoryComposer(self)

    # ─── SESSION CONVENIENCE ─────────────────────────────────

    def warm_up(self) -> bool:
        """
        Warm up the session by loading instagram.com.

        Captures x-ig-www-claim (HMAC token) and x-instagram-ajax (build hash).
        Called automatically on first request, but can be called manually.

        Returns:
            True if warm-up was successful
        """
        sess = self._session_mgr.get_session()
        if not sess:
            return False
        return self._client._warm_up_session(sess)

    def save_session(self, filepath: str = "session.json") -> None:
        """Save current session to file. Shortcut for ig.auth.save_session()."""
        self.auth.save_session(filepath)

    def load_session(self, filepath: str = "session.json") -> bool:
        """Load session from file. Shortcut for ig.auth.load_session()."""
        return self.auth.load_session(filepath)

    # ─── FACTORY METHODS ─────────────────────────────────────

    @classmethod
    def from_session_file(
        cls,
        filepath: str = "session.json",
        debug: bool = False,
        debug_log_file: Optional[str] = None,
        **kwargs,
    ) -> "Instagram":
        """
        Create client by loading a previously saved session.

        Usage:
            ig = Instagram.from_session_file("session.json")
            ig = Instagram.from_session_file("session.json", debug=True)
        """
        ig = cls(
            session_file=filepath,
            debug=debug,
            debug_log_file=debug_log_file,
            **kwargs,
        )
        ig.load_session(filepath)
        return ig

    @classmethod
    def anonymous(
        cls,
        unlimited: bool = False,
        profile_strategies=None,
        posts_strategies=None,
    ) -> "Instagram":
        """
        Create anonymous-only client (no login, no .env).

        Args:
            unlimited: If True, disable all rate limiting and delays
                      for maximum scraping speed.
            profile_strategies: Custom profile strategy order.
                               Default: ["web_api", "graphql", "html_parse"]
            posts_strategies: Custom posts strategy order.
                             Default: ["web_api", "html_parse", "graphql", "mobile_feed"]

        Usage:
            ig = Instagram.anonymous()
            profile = ig.public.get_profile('cristiano')

            # Custom strategy:
            ig = Instagram.anonymous(
                unlimited=True,
                profile_strategies=["web_api", "html_parse"],
                posts_strategies=["mobile_feed", "web_api"],
            )
        """
        instance = cls(rate_limiting=not unlimited)
        # Override anonymous client with unlimited flag + strategies
        instance._anon_client = AnonClient(
            anti_detect=instance._anti_detect,
            proxy_manager=instance._proxy_mgr,
            unlimited=unlimited,
            profile_strategies=profile_strategies,
            posts_strategies=posts_strategies,
        )
        # Evict cached public/public_data so the lazy factories rebuild
        # them against the new _anon_client on next access.
        instance.__dict__.pop("public", None)
        instance.__dict__.pop("public_data", None)
        return instance

    @classmethod
    def from_cookie_file(
        cls,
        cookie_path: str,
        debug: bool = False,
        **kwargs,
    ) -> "Instagram":
        """
        Create client from browser-exported cookie JSON file.

        The file should be a JSON array of cookie objects exported
        from browser (e.g. via EditThisCookie or Cookie-Editor):
            [{"name": "sessionid", "value": "...", "domain": ".instagram.com"}, ...]

        Usage:
            ig = Instagram.from_cookie_file("cookies.json")
            user = ig.users.get_by_username("cristiano")
        """
        instance = cls(debug=debug, **kwargs)
        sess = instance._session_mgr.load_from_browser_cookies(cookie_path)
        if not sess:
            raise ValueError(f"Failed to load cookies from {cookie_path}")
        instance._sync_anon_cookies()
        return instance

    @classmethod
    def from_cookie_dir(
        cls,
        dir_path: str,
        debug: bool = False,
        **kwargs,
    ) -> "Instagram":
        """
        Create client with multiple sessions from a directory of cookie files.

        Each .json file in the directory should contain browser-exported cookies.
        Sessions are used in round-robin rotation.

        Usage:
            ig = Instagram.from_cookie_dir("./sessions/")
            # Uses different session for each request
            user1 = ig.users.get_by_username("cristiano")
            user2 = ig.users.get_by_username("messi")

            # Check pool health
            print(ig.pool_status())
        """
        instance = cls(debug=debug, **kwargs)
        count = instance._session_mgr.load_from_cookie_dir(dir_path)
        if count == 0:
            raise ValueError(f"No valid cookie files found in {dir_path}")
        return instance

    def pool_status(self) -> dict:
        """Get session pool monitoring status. See SessionManager.get_pool_status()."""
        return self._session_mgr.get_pool_status()

    # ─── LOGIN CONVENIENCE ───────────────────────────────────

    def login(self, username: str, password: str, **kwargs):
        """
        Login with username/password.
        Shortcut — calls ig.auth.login().
        """
        return self.auth.login(username, password, **kwargs)

    @classmethod
    def from_env(
        cls,
        env_path: str = ".env",
        rate_limiting: bool = True,
        debug: bool = False,
        debug_log_file: Optional[str] = None,
    ) -> "Instagram":
        """
        Create Instagram client from .env file.

        .env format:
            SESSION_ID=...
            CSRF_TOKEN=...
            DS_USER_ID=...
            MID=...
            IG_DID=...
            DATR=...
            USER_AGENT=...

        For multiple accounts:
            SESSION_ID_2=...
            CSRF_TOKEN_2=...
            DS_USER_ID_2=...

        Args:
            env_path: Path to .env file
            rate_limiting: Enable rate limiting
            debug: Enable structured debug logging
            debug_log_file: Debug log file path

        Returns:
            Instagram instance
        """
        instance = cls(
            rate_limiting=rate_limiting,
            debug=debug,
            debug_log_file=debug_log_file,
        )
        instance._session_mgr.load_from_env(env_path)
        instance._sync_anon_cookies()

        if instance._session_mgr.session_count == 0:
            logger.warning(
                f"No sessions found! Check {env_path}. "
                "SESSION_ID, CSRF_TOKEN, DS_USER_ID are required."
            )

        # Debug: log session info
        if debug and instance._session_mgr.session_count > 0:
            sess = instance._session_mgr.get_session()
            if sess:
                instance._debug.session_info(
                    ds_user_id=sess.ds_user_id,
                    csrf_token=sess.csrf_token,
                    ig_www_claim=sess.ig_www_claim,
                    session_id=sess.session_id,
                    user_agent=sess.user_agent,
                )

        return instance

    def _sync_anon_cookies(self):
        """
        Sync session cookies to AnonClient.
        Called after sessions are loaded post-init (from_env, from_cookie_file).
        """
        if self._session_mgr.session_count == 0:
            return
        sess = self._session_mgr.get_session()
        if not sess:
            return
        cookies = {
            "sessionid": sess.session_id,
            "ds_user_id": sess.ds_user_id,
        }
        if getattr(sess, 'csrf_token', None):
            cookies["csrftoken"] = sess.csrf_token
        if getattr(sess, 'mid', None):
            cookies["mid"] = sess.mid
        if getattr(sess, 'ig_did', None):
            cookies["ig_did"] = sess.ig_did
        if getattr(sess, 'datr', None):
            cookies["datr"] = sess.datr
        self._anon_client._cookies = cookies

    # ─── Proxy management ────────────────────────────────────────

    def add_proxies(self, proxy_urls: List[str]) -> "Instagram":
        """
        Add proxies.

        Supported formats:
            - socks5://ip:port
            - socks5://user:pass@ip:port
            - http://ip:port
            - http://user:pass@ip:port
            - https://ip:port

        Args:
            proxy_urls: List of proxy URLs

        Returns:
            self (for chaining)
        """
        self._proxy_mgr.add_proxies(proxy_urls)
        return self

    def add_proxy(self, proxy_url: str) -> "Instagram":
        """Add a single proxy."""
        self._proxy_mgr.add_proxy(proxy_url)
        return self

    def load_proxies_from_file(self, filepath: str) -> "Instagram":
        """
        Load proxies from file (one proxy per line).

        Args:
            filepath: Path to proxy file
        """
        with open(filepath, "r") as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        self._proxy_mgr.add_proxies(proxies)
        return self

    def set_proxy_strategy(self, strategy: str) -> "Instagram":
        """
        Change proxy rotation strategy.

        Args:
            strategy: "round_robin", "random", "weighted"
        """
        strat_map = {
            "round_robin": RotationStrategy.ROUND_ROBIN,
            "random": RotationStrategy.RANDOM,
            "weighted": RotationStrategy.WEIGHTED,
        }
        self._proxy_mgr.set_strategy(strat_map.get(strategy, RotationStrategy.WEIGHTED))
        return self

    # ─── Session management ──────────────────────────────────────

    def add_session(
        self,
        session_id: str,
        csrf_token: str,
        ds_user_id: str,
        **kwargs,
    ) -> "Instagram":
        """
        Add an additional account.

        Args:
            session_id: Instagram session cookie
            csrf_token: CSRF token
            ds_user_id: User ID
        """
        self._session_mgr.add_session(
            session_id=session_id,
            csrf_token=csrf_token,
            ds_user_id=ds_user_id,
            **kwargs,
        )
        return self

    # ─── Settings ─────────────────────────────────────────────

    def set_rate_limiting(self, enabled: bool) -> "Instagram":
        """Enable/disable rate limiting."""
        self._rate_limiter.enabled = enabled
        return self

    def rotate_identity(self) -> "Instagram":
        """Force browser identity rotation (fingerprint, UA, headers)."""
        self._anti_detect.rotate_identity()
        return self

    # ─── Info ───────────────────────────────────────────────

    @property
    def proxy_stats(self) -> dict:
        """Proxy statistics."""
        return self._proxy_mgr.get_stats()

    @property
    def session_count(self) -> int:
        """Active sessions count."""
        return self._session_mgr.active_count

    @property
    def request_count(self) -> int:
        """Total requests count."""
        return self._anti_detect.request_count

    # ─── Context manager ────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        """Clean up resources."""
        self._client.close()

    def __repr__(self) -> str:
        return (
            f"<Instagram sessions={self._session_mgr.session_count} "
            f"proxies={self._proxy_mgr.active_count} "
            f"requests={self._anti_detect.request_count}>"
        )
