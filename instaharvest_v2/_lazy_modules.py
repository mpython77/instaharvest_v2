"""
Lazy API Module Registry
=========================
Registry of factory callables for every API module exposed on the
`Instagram` class. Modules are imported and instantiated only when first
accessed via attribute lookup.

Why:
    The previous `Instagram.__init__()` eagerly imported and instantiated
    30+ API modules, causing:
        - Long startup time (~200-400ms of imports).
        - High memory footprint even when only one module is used.
        - Tight coupling: adding a module required editing __init__.

Design:
    A single LAZY_API_MODULES mapping declares attribute name -> factory.
    Each factory takes the Instagram instance and returns the constructed
    module. The Instagram class implements __getattr__ to dispatch.

    Inter-module dependencies are resolved naturally: when `feed` factory
    accesses `self.graphql`, that triggers the graphql factory if not yet
    constructed, recursively building the dependency graph on demand.

Adding a new API module:
    1. Add an entry to LAZY_API_MODULES below.
    2. The new attribute is automatically available on every Instagram
       instance (and AsyncInstagram, if added there).
"""

import importlib
from typing import Any, Callable, Dict, Optional, Tuple


# Type alias for a module factory: receives the Instagram instance,
# returns the constructed API module.
ModuleFactory = Callable[[Any], Any]


# ─── Authenticated API factories ───────────────────────────


def _make_users(ig: Any) -> Any:
    from .api.users import UsersAPI
    return UsersAPI(ig._client)


def _make_media(ig: Any) -> Any:
    from .api.media import MediaAPI
    return MediaAPI(ig._client)


def _make_graphql(ig: Any) -> Any:
    from .api.graphql import GraphQLAPI
    return GraphQLAPI(ig._client)


def _make_feed(ig: Any) -> Any:
    from .api.feed import FeedAPI
    # feed depends on graphql (auto-constructed via __getattr__ if needed)
    return FeedAPI(ig._client, graphql=ig.graphql)


def _make_search(ig: Any) -> Any:
    from .api.search import SearchAPI
    return SearchAPI(ig._client)


def _make_hashtags(ig: Any) -> Any:
    from .api.hashtags import HashtagsAPI
    return HashtagsAPI(ig._client)


def _make_friendships(ig: Any) -> Any:
    from .api.friendships import FriendshipsAPI
    return FriendshipsAPI(ig._client)


def _make_direct(ig: Any) -> Any:
    from .api.direct import DirectAPI
    return DirectAPI(ig._client)


def _make_stories(ig: Any) -> Any:
    from .api.stories import StoriesAPI
    return StoriesAPI(ig._client)


def _make_insights(ig: Any) -> Any:
    from .api.insights import InsightsAPI
    return InsightsAPI(ig._client)


def _make_account(ig: Any) -> Any:
    from .api.account import AccountAPI
    return AccountAPI(ig._client)


def _make_notifications(ig: Any) -> Any:
    from .api.notifications import NotificationsAPI
    return NotificationsAPI(ig._client)


def _make_upload(ig: Any) -> Any:
    from .api.upload import UploadAPI
    return UploadAPI(ig._client)


def _make_location(ig: Any) -> Any:
    from .api.location import LocationAPI
    return LocationAPI(ig._client)


def _make_collections(ig: Any) -> Any:
    from .api.collections import CollectionsAPI
    return CollectionsAPI(ig._client)


def _make_download(ig: Any) -> Any:
    from .api.download import DownloadAPI
    return DownloadAPI(ig._client)


def _make_auth(ig: Any) -> Any:
    from .api.auth import AuthAPI
    return AuthAPI(ig._client)


def _make_discover(ig: Any) -> Any:
    from .api.discover import DiscoverAPI
    return DiscoverAPI(ig._client)


# ─── High-level (composing) API factories ──────────────────


def _make_export(ig: Any) -> Any:
    from .api.export import ExportAPI
    return ExportAPI(
        ig._client, ig.users, ig.friendships, ig.media, ig.hashtags,
    )


def _make_analytics(ig: Any) -> Any:
    from .api.analytics import AnalyticsAPI
    return AnalyticsAPI(ig._client, ig.users, ig.media, ig.feed)


def _make_scheduler(ig: Any) -> Any:
    from .api.scheduler import SchedulerAPI
    return SchedulerAPI(ig.upload, ig.stories)


def _make_growth(ig: Any) -> Any:
    from .api.growth import GrowthAPI
    return GrowthAPI(ig._client, ig.users, ig.friendships)


def _make_automation(ig: Any) -> Any:
    from .api.automation import AutomationAPI
    return AutomationAPI(
        ig._client, ig.direct, ig.media, ig.friendships, ig.stories,
    )


def _make_monitor(ig: Any) -> Any:
    from .api.monitor import MonitorAPI
    return MonitorAPI(ig._client, ig.users, ig.feed, ig.stories)


def _make_bulk_download(ig: Any) -> Any:
    from .api.bulk_download import BulkDownloadAPI
    return BulkDownloadAPI(ig._client, ig.download, ig.users, ig.stories)


def _make_hashtag_research(ig: Any) -> Any:
    from .api.hashtag_research import HashtagResearchAPI
    return HashtagResearchAPI(ig._client, ig.hashtags)


def _make_pipeline(ig: Any) -> Any:
    from .api.pipeline import PipelineAPI
    return PipelineAPI(ig._client, ig.users, ig.friendships, ig.media)


def _make_ai_suggest(ig: Any) -> Any:
    from .api.ai_suggest import AISuggestAPI
    return AISuggestAPI(
        ig._client, ig.users, ig.hashtags, ig.hashtag_research,
    )


def _make_audience(ig: Any) -> Any:
    from .api.audience import AudienceAPI
    return AudienceAPI(ig._client, ig.users, ig.friendships)


def _make_comment_manager(ig: Any) -> Any:
    from .api.comment_manager import CommentManagerAPI
    return CommentManagerAPI(ig._client, ig.media)


def _make_ab_test(ig: Any) -> Any:
    from .api.ab_test import ABTestAPI
    return ABTestAPI(ig._client, ig.upload, ig.media, ig.analytics)


# ─── Anonymous / public-data factories ─────────────────────


def _make_public(ig: Any) -> Any:
    from .api.public import PublicAPI
    return PublicAPI(ig._anon_client)


def _make_public_data(ig: Any) -> Any:
    from .api.public_data import PublicDataAPI
    return PublicDataAPI(ig.public)


# ─── Registry ──────────────────────────────────────────────


LAZY_API_MODULES: Dict[str, ModuleFactory] = {
    # Low-level
    "users": _make_users,
    "media": _make_media,
    "graphql": _make_graphql,
    "feed": _make_feed,
    "search": _make_search,
    "hashtags": _make_hashtags,
    "friendships": _make_friendships,
    "direct": _make_direct,
    "stories": _make_stories,
    "insights": _make_insights,
    "account": _make_account,
    "notifications": _make_notifications,
    "upload": _make_upload,
    "location": _make_location,
    "collections": _make_collections,
    "download": _make_download,
    "auth": _make_auth,
    "discover": _make_discover,
    # High-level (depend on low-level)
    "export": _make_export,
    "analytics": _make_analytics,
    "scheduler": _make_scheduler,
    "growth": _make_growth,
    "automation": _make_automation,
    "monitor": _make_monitor,
    "bulk_download": _make_bulk_download,
    "hashtag_research": _make_hashtag_research,
    "pipeline": _make_pipeline,
    "ai_suggest": _make_ai_suggest,
    "audience": _make_audience,
    "comment_manager": _make_comment_manager,
    "ab_test": _make_ab_test,
    # Public / anonymous
    "public": _make_public,
    "public_data": _make_public_data,
}


# Public list for introspection / documentation tools.
LAZY_MODULE_NAMES: tuple = tuple(LAZY_API_MODULES.keys())


def _lazy_factory(
    rel_module: str,
    cls_name: str,
    deps: Tuple[str, ...] = ("_client",),
    kw_deps: Optional[Dict[str, str]] = None,
    pass_self: bool = False,
) -> ModuleFactory:
    """Create a lazy factory that imports ``cls_name`` and injects dependencies."""

    def _factory(ig: Any) -> Any:
        mod = importlib.import_module(rel_module, package=__package__)
        cls = getattr(mod, cls_name)
        args = (ig,) if pass_self else tuple(getattr(ig, dep) for dep in deps)
        kwargs = {k: getattr(ig, dep) for k, dep in (kw_deps or {}).items()}
        return cls(*args, **kwargs)

    return _factory


def resolve_lazy_module(
    instance: Any,
    name: str,
    registry: Dict[str, ModuleFactory],
) -> Any:
    """Resolve, cache on ``instance.__dict__``, and return a lazy API module."""
    # Avoid recursion during early construction (before _client is set)
    if name.startswith("_"):
        raise AttributeError(
            f"{type(instance).__name__!r} has no attribute {name!r}"
        )

    factory = registry.get(name)
    if factory is None:
        raise AttributeError(
            f"{type(instance).__name__!r} has no attribute {name!r}"
        )

    try:
        module = factory(instance)
    except Exception as exc:
        raise AttributeError(
            f"Failed to load API module {name!r}: {type(exc).__name__}: {exc}"
        ) from exc

    instance.__dict__[name] = module
    return module


# ─── Async Registry (for AsyncInstagram) ───────────────────


_ASYNC_MODULE_SPECS: Tuple[Tuple[str, str, str, Tuple[str, ...], Optional[Dict[str, str]], bool], ...] = (
    # Low-level async modules
    ("users", ".api.async_users", "AsyncUsersAPI", ("_client",), None, False),
    ("media", ".api.async_media", "AsyncMediaAPI", ("_client",), None, False),
    ("friendships", ".api.async_friendships", "AsyncFriendshipsAPI", ("_client",), None, False),
    ("graphql", ".api.async_graphql", "AsyncGraphQLAPI", ("_client",), None, False),
    ("feed", ".api.async_feed", "AsyncFeedAPI", ("_client",), {"graphql": "graphql"}, False),
    ("stories", ".api.async_stories", "AsyncStoriesAPI", ("_client",), None, False),
    ("direct", ".api.async_direct", "AsyncDirectAPI", ("_client",), None, False),
    ("search", ".api.async_search", "AsyncSearchAPI", ("_client",), None, False),
    ("upload", ".api.async_upload", "AsyncUploadAPI", ("_client",), None, False),
    ("hashtags", ".api.async_hashtags", "AsyncHashtagsAPI", ("_client",), None, False),
    ("insights", ".api.async_insights", "AsyncInsightsAPI", ("_client",), None, False),
    ("account", ".api.async_account", "AsyncAccountAPI", ("_client",), None, False),
    ("notifications", ".api.async_notifications", "AsyncNotificationsAPI", ("_client",), None, False),
    ("location", ".api.async_location", "AsyncLocationAPI", ("_client",), None, False),
    ("collections", ".api.async_collections", "AsyncCollectionsAPI", ("_client",), None, False),
    ("download", ".api.async_download", "AsyncDownloadAPI", ("_client",), None, False),
    ("auth", ".api.async_auth", "AsyncAuthAPI", ("_client",), None, False),
    ("discover", ".api.async_discover", "AsyncDiscoverAPI", ("_client",), None, False),
    # High-level async modules (composing low-level APIs)
    ("export", ".api.async_export", "AsyncExportAPI", ("_client", "users", "friendships", "media", "hashtags"), None, False),
    ("analytics", ".api.async_analytics", "AsyncAnalyticsAPI", ("_client", "users", "media", "feed"), None, False),
    ("scheduler", ".api.async_scheduler", "AsyncSchedulerAPI", ("upload", "stories"), None, False),
    ("growth", ".api.async_growth", "AsyncGrowthAPI", ("_client", "users", "friendships"), None, False),
    ("automation", ".api.async_automation", "AsyncAutomationAPI", ("_client", "direct", "media", "friendships", "stories"), None, False),
    ("monitor", ".api.async_monitor", "AsyncMonitorAPI", ("_client", "users", "feed", "stories"), None, False),
    ("bulk_download", ".api.async_bulk_download", "AsyncBulkDownloadAPI", ("_client", "download", "users", "stories"), None, False),
    ("hashtag_research", ".api.async_hashtag_research", "AsyncHashtagResearchAPI", ("_client", "hashtags"), None, False),
    ("pipeline", ".api.async_pipeline", "AsyncPipelineAPI", ("_client", "users", "friendships", "media"), None, False),
    ("ai_suggest", ".api.async_ai_suggest", "AsyncAISuggestAPI", ("_client", "users", "hashtags", "hashtag_research"), None, False),
    ("audience", ".api.async_audience", "AsyncAudienceAPI", ("_client", "users", "friendships"), None, False),
    ("comment_manager", ".api.async_comment_manager", "AsyncCommentManagerAPI", ("_client", "media"), None, False),
    ("ab_test", ".api.async_ab_test", "AsyncABTestAPI", ("_client", "upload", "media", "analytics"), None, False),
    # Batch + Anonymous / public-data
    ("batch", ".batch", "BatchAPI", (), None, True),
    ("public", ".api.async_public", "AsyncPublicAPI", ("_anon_client",), None, False),
    ("public_data", ".api.async_public_data", "AsyncPublicDataAPI", ("public",), None, False),
)


LAZY_ASYNC_API_MODULES: Dict[str, ModuleFactory] = {
    attr: _lazy_factory(mod_path, cls_name, deps, kw_deps, pass_self)
    for attr, mod_path, cls_name, deps, kw_deps, pass_self in _ASYNC_MODULE_SPECS
}


LAZY_ASYNC_MODULE_NAMES: tuple = tuple(LAZY_ASYNC_API_MODULES.keys())
