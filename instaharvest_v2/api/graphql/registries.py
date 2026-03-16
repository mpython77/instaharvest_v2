"""
GraphQL Query Registries
========================
Hash and doc_id registries for Instagram GraphQL API.

- QUERY_HASHES: Legacy query hashes (GET /graphql/query/?query_hash=...)
- DOC_IDS: Modern document IDs (POST /graphql/query with doc_id=...)
"""

# Legacy query_hashes (GET /graphql/query/?query_hash=...)
QUERY_HASHES = {
    "followers": "c76146de99bb02f6415203be841dd25a",
    "following": "d04b0a864b4b54837c0d870b0e77e076",
    "user_posts": "69cba40317214236af40e7efa697781d",
    "tagged_posts": "ff260833edf142571571f991cb0fcd26",
    "liked_posts": "d5d763b1e2acf209d62d22d184488e57",
    "user_reels": "303a4ac7f6bb47272571a1a111c50829",
    "saved_posts": "2ce1d673055b99c84dc0d5b62e3f30d2",
    "comments": "bc3296d1ce80a24b1b6e40b1e72903f5",
    "likers": "d5d763b1e2acf209d62d22d184488e57",
}

# Modern doc_ids (POST /graphql/query with doc_id=...)
DOC_IDS = {
    # User profile info
    "profile_info": "9496468463735694",
    # User profile posts (pagination)
    "profile_posts": "26442143102071041",
    # User reels tab
    "profile_reels": "25475393498805108",
    # User tagged posts
    "profile_tagged": "26832701866332833",
    # User hover card (mini profile popup)
    "profile_hover_card": "26120562547638331",
    # Story highlights tray
    "profile_highlights": "9814547265267853",
    # Suggested users on profile
    "profile_suggested": "25814188068245954",
    # Profile page content (full) — updated 2026-03
    "profile_page_content": "34272012165747896",
    # Mark story as seen (mutation)
    "stories_seen": "24372833149008516",
    # Like a post (mutation)
    "like_media": "23951234354462179",
    # Search initial state (trending)
    "search_null_state": "31090951390548929",
    # User feed timeline (initial load)
    "feed_timeline": "26307883352181852",
    # User feed timeline (pagination / subsequent pages)
    "feed_timeline_pagination": "26038778959150000",
    # Liked posts feed (UNVERIFIED — REST fallback available)
    "feed_liked": "9863315953735856",
    # Saved/bookmarked posts feed
    "feed_saved": "26523442937261068",
    # Hashtag feed (UNVERIFIED — REST fallback available)
    "feed_tag": "9506655819362310",
    # Reels trending feed
    "feed_reels_trending": "26136666099278270",
    # Post comments
    "media_comments": "26653752520898584",
    # Comment thread / replies (UNVERIFIED)
    "comment_thread": "37264637455117356",
    # Post likers (UNVERIFIED — REST /api/v1/media/{id}/likers/ available)
    "media_likers": "9321654614509578",
    # Followers list (UNVERIFIED — REST /api/v1/friendships/{id}/followers/ available)
    "followers": "37479062552899498",
    # Following list (UNVERIFIED — REST /api/v1/friendships/{id}/following/ available)
    "following": "37266564218498392",
    # Story reels tray
    "story_tray": "26695923807960093",
    # Post detail
    "media_detail": "8845758582119845",
    # Search suggestions
    "search_top": "36645594540471822",
    # Explore page
    "explore_grid": "32040227643110105",
    # Check if new feed posts exist
    "check_new_feed_posts": "34054231004223565",
    # DM inbox badge/threads (Iris subscription)
    "dm_inbox": "33328371206806736",
    # DM sync (Lightspeed protocol — full thread/message sync)
    "dm_sync_lightspeed": "9859601450795492",
    # Stories tray v3 (UNVERIFIED — suggestedUsers module error; use story_tray instead)
    "story_tray_v3": "25945596851746603",
    # Encrypted credentials / fr cookie
    "get_fr_cookie": "27116338451299930",
    # Highlights page items (batch fetch with pagination)
    "highlights_items": "25607114268966978",
    # Profile tagged tab v2 (PolarisProfileTaggedTabContentQuery)
    "profile_tagged_v2": "34661906216741021",
    # Location page posts (ranked/recent by location_id)
    "location_posts": "25930113323318595",
    # Profile reels tab v2 (PolarisProfileReelsTabContentQuery — play_count, like_count)
    "profile_reels_v2": "34185899317723021",
    # COPPA enforcement check (viewer age restriction status)
    "coppa_check": "24797863709808827",
}
