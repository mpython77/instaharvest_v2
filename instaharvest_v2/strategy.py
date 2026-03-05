"""
Strategy Configuration
======================
Configurable strategy chain for anonymous scraping.
Users can control which strategies are used and in what order.

Usage:
    # Default (web_api first — best data):
    ig = Instagram.anonymous()

    # Custom order:
    ig = Instagram.anonymous(
        profile_strategies=["html_parse", "web_api"],
        posts_strategies=["mobile_feed", "web_api"],
    )
"""

from enum import Enum
from typing import List, Optional, Sequence, Union


class ProfileStrategy(str, Enum):
    """Profile scraping strategies (ordered by data richness)."""
    WEB_API = "web_api"        # Best: bio_links, category, business_email, external_url
    GRAPHQL = "graphql"        # Good: followers, bio, posts_count
    HTML_PARSE = "html_parse"  # Minimal: followers, short bio (no bio_links/category)


class PostsStrategy(str, Enum):
    """Posts scraping strategies."""
    WEB_API = "web_api"          # 12 posts from web_profile_info
    HTML_PARSE = "html_parse"    # Embedded posts from HTML page
    GRAPHQL = "graphql"          # GraphQL query_hash (needs user_id)
    MOBILE_FEED = "mobile_feed"  # Mobile API — richest data (video_url, location)


# ═══════════════════════════════════════════════════════════
# Default strategy chains — web_api first for best data
# ═══════════════════════════════════════════════════════════

DEFAULT_PROFILE_STRATEGIES: List[ProfileStrategy] = [
    ProfileStrategy.WEB_API,
    ProfileStrategy.GRAPHQL,
    ProfileStrategy.HTML_PARSE,
]

DEFAULT_POSTS_STRATEGIES: List[PostsStrategy] = [
    PostsStrategy.WEB_API,
    PostsStrategy.HTML_PARSE,
    PostsStrategy.GRAPHQL,
    PostsStrategy.MOBILE_FEED,
]


def parse_profile_strategies(
    value: Optional[Sequence[Union[str, ProfileStrategy]]] = None,
) -> List[ProfileStrategy]:
    """Parse user input into ProfileStrategy list."""
    if value is None:
        return DEFAULT_PROFILE_STRATEGIES.copy()
    result = []
    for item in value:
        if isinstance(item, ProfileStrategy):
            result.append(item)
        elif isinstance(item, str):
            result.append(ProfileStrategy(item))
        else:
            raise ValueError(f"Invalid profile strategy: {item}")
    return result


def parse_posts_strategies(
    value: Optional[Sequence[Union[str, PostsStrategy]]] = None,
) -> List[PostsStrategy]:
    """Parse user input into PostsStrategy list."""
    if value is None:
        return DEFAULT_POSTS_STRATEGIES.copy()
    result = []
    for item in value:
        if isinstance(item, PostsStrategy):
            result.append(item)
        elif isinstance(item, str):
            result.append(PostsStrategy(item))
        else:
            raise ValueError(f"Invalid posts strategy: {item}")
    return result
