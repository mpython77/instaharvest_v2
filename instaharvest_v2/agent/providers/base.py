"""
Base AI Provider
================
Abstract interface for AI model providers.
All providers (OpenAI, Gemini, etc.) implement this interface.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("instaharvest_v2.agent.providers")


@dataclass
class ToolCall:
    """A tool call requested by the AI."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ProviderResponse:
    """Response from an AI provider."""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# InstaHarvest v2 tools schema — shared across providers
instaharvest_v2_TOOLS = [
    {
        "name": "run_instaharvest_v2_code",
        "description": (
            "Execute Python code that uses the InstaHarvest v2 library. "
            "The `ig` variable is a pre-configured Instagram client. "
            "Output results via print() or assign to a `result` variable. "
            "The sandbox includes: json, csv, re, math, datetime, pathlib."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code using InstaHarvest v2 (ig variable is available)",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what the code does",
                },
            },
            "required": ["code", "description"],
        },
    },
    {
        "name": "save_to_file",
        "description": (
            "Save content to a file. Supported formats: "
            "CSV, JSON, JSONL, TXT, MD, TSV, XLSX (Excel). "
            "Only relative paths in the current directory are allowed. "
            "Returns full absolute path of the saved file. "
            "For Excel (.xlsx): pass JSON content (list of dicts or dict) — "
            "it will be auto-converted to Excel with headers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name with extension (e.g. results.json, data.csv)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user a question to get additional information. "
            "Use when you need: username, credentials, preferences, "
            "file paths, or confirmation for sensitive actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question to ask the user",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read contents of a file from the current directory. "
            "Supports: CSV, JSON, JSONL, TXT, MD, TSV. "
            "Use to load previously saved data or check existing files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name to read (e.g. data.csv, results.json)",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to read (default: 100, max: 500)",
                },
            },
            "required": ["filename"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List files and directories in the current working directory "
            "or a specific subdirectory. Shows file names, sizes, and types."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to list (default: current directory '.')",
                },
                "pattern": {
                    "type": "string",
                    "description": "Optional glob pattern filter (e.g. '*.csv', '*.json')",
                },
            },
        },
    },
    {
        "name": "download_media",
        "description": (
            "Download Instagram media (photos, videos, stories, reels) "
            "to a local directory. Supports single posts, profile pics, "
            "and bulk downloads."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Instagram URL (post, reel, story) or username",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Output directory (default: 'downloads/')",
                },
                "media_type": {
                    "type": "string",
                    "description": "Type: 'post', 'profile_pic', 'stories', 'reels', 'all'",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "analyze_data",
        "description": (
            "Analyze data from a file or raw data. Compute statistics, "
            "counts, averages, top/bottom items, distributions. "
            "Returns formatted analysis report."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "File path (data.csv, results.json) or raw JSON data",
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type: 'summary', 'top_n', 'distribution', 'compare', 'trend'",
                },
                "field": {
                    "type": "string",
                    "description": "Field/column to analyze (e.g. 'follower_count', 'like_count')",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top/bottom items to show (default: 10)",
                },
            },
            "required": ["source", "analysis_type"],
        },
    },
    {
        "name": "http_request",
        "description": (
            "Make an HTTP GET or POST request to an external API or URL. "
            "Returns the response body. Use for fetching public data, "
            "webhooks, or integrating with external services."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method: 'GET' or 'POST'",
                },
                "url": {
                    "type": "string",
                    "description": "Full URL to request",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers as key-value pairs",
                },
                "body": {
                    "type": "string",
                    "description": "Optional request body (for POST)",
                },
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "create_chart",
        "description": (
            "Create a chart/visualization from data and save as an image file. "
            "Supported types: bar, line, pie, horizontal_bar. "
            "Returns the saved image file path."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "description": "Type: 'bar', 'line', 'pie', 'horizontal_bar'",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "X-axis labels or category names",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Y-axis values or quantities",
                },
                "filename": {
                    "type": "string",
                    "description": "Output file name (default: chart.png)",
                },
            },
            "required": ["chart_type", "title", "labels", "values"],
        },
    },
    {
        "name": "search_web",
        "description": (
            "Search the web for information. Use when you need "
            "current data, trends, news, or facts that are not "
            "available in the InstaHarvest v2 library."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
            },
            "required": ["query"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # SPECIALIZED INSTAGRAM TOOLS — Direct API calls, no code needed!
    # ═══════════════════════════════════════════════════════════
    {
        "name": "get_profile",
        "description": (
            "Get Instagram profile information by username. "
            "Returns: username, full_name, followers, following, posts_count, "
            "biography, profile_pic_url. Works in both anonymous and login mode. "
            "USE THIS instead of run_instaharvest_v2_code for profile queries!"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username (without @)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_posts",
        "description": (
            "Get a user's recent Instagram posts with likes, comments, captions. "
            "Returns formatted list of posts. Works in anonymous mode. "
            "USE THIS instead of run_instaharvest_v2_code for post queries!"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum posts to fetch (default: 12, max: 50)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "search_users",
        "description": (
            "Search Instagram for users by query string. "
            "Returns list of matching users with username, full_name, followers. "
            "USE THIS instead of run_instaharvest_v2_code for user searches!"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (name, username, keyword)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_user_info",
        "description": (
            "Get detailed user information including verification status, "
            "business category, contact info. In login mode returns full data. "
            "In anonymous mode, falls back to get_profile with limited data. "
            "USE THIS when user asks about verification, business info, or detailed profile."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
            },
            "required": ["username"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # FRIENDSHIPS TOOLS — Follow, unfollow, followers/following lists
    # ═══════════════════════════════════════════════════════════
    {
        "name": "follow_user",
        "description": (
            "Follow or unfollow an Instagram user. REQUIRES LOGIN. "
            "Returns success/failure message."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username to follow/unfollow",
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'follow' or 'unfollow'",
                },
            },
            "required": ["username", "action"],
        },
    },
    {
        "name": "get_followers",
        "description": (
            "Get list of followers for a user. REQUIRES LOGIN. "
            "Returns list of usernames with follower counts. "
            "USE THIS when user asks 'who follows X' or 'X ning followerlari'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum followers to fetch (default: 50, max: 1000)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_following",
        "description": (
            "Get list of accounts a user follows. REQUIRES LOGIN. "
            "Returns list of usernames. "
            "USE THIS when user asks 'who does X follow' or 'X kim follow qiladi'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum following to fetch (default: 50, max: 1000)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_friendship_status",
        "description": (
            "Check relationship between you and another user. REQUIRES LOGIN. "
            "Returns: do I follow them? Do they follow me? Blocked? Muted? "
            "USE THIS when user asks 'do I follow X' or 'does X follow me'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username to check",
                },
            },
            "required": ["username"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # MEDIA TOOLS — Like, comment, post info
    # ═══════════════════════════════════════════════════════════
    {
        "name": "like_media",
        "description": (
            "Like or unlike an Instagram post/reel. REQUIRES LOGIN. "
            "Accepts post URL or media ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "string",
                    "description": "Media PK/ID or Instagram URL (https://instagram.com/p/...)",
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'like' or 'unlike' (default: 'like')",
                },
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "comment_media",
        "description": (
            "Add a comment to an Instagram post/reel. REQUIRES LOGIN. "
            "Returns the posted comment data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "string",
                    "description": "Media PK/ID or Instagram URL",
                },
                "text": {
                    "type": "string",
                    "description": "Comment text",
                },
            },
            "required": ["media_id", "text"],
        },
    },
    {
        "name": "get_media_info",
        "description": (
            "Get full information about a specific post/reel. "
            "Returns: likes, comments, caption, media type, owner, url. "
            "Works with both media ID and Instagram URL. "
            "USE THIS when user asks about a specific post."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {
                    "type": "string",
                    "description": "Media PK/ID or Instagram URL (https://instagram.com/p/...)",
                },
            },
            "required": ["media_id"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # STORIES TOOL
    # ═══════════════════════════════════════════════════════════
    {
        "name": "get_stories",
        "description": (
            "Get Instagram stories for a user. REQUIRES LOGIN. "
            "Returns list of story items with type, timestamp, media URLs. "
            "USE THIS when user asks for someone's stories."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
            },
            "required": ["username"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # DIRECT MESSAGE TOOL
    # ═══════════════════════════════════════════════════════════
    {
        "name": "send_dm",
        "description": (
            "Send a direct message to a user. REQUIRES LOGIN. "
            "Can send text messages to existing threads or create new ones."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Recipient username (for new thread)",
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send",
                },
                "thread_id": {
                    "type": "string",
                    "description": "Existing thread ID (if known, optional)",
                },
            },
            "required": ["text"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # HASHTAG TOOL
    # ═══════════════════════════════════════════════════════════
    {
        "name": "get_hashtag_info",
        "description": (
            "Get hashtag information: post count, top posts, related content. "
            "Works WITHOUT login using public API. "
            "USE THIS when user asks about a hashtag's popularity or info."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {
                    "type": "string",
                    "description": "Hashtag name (without #)",
                },
            },
            "required": ["hashtag"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # ACCOUNT TOOL
    # ═══════════════════════════════════════════════════════════
    {
        "name": "get_my_account",
        "description": (
            "Get current logged-in user account information. REQUIRES LOGIN. "
            "Returns: username, followers, following, bio, verification status. "
            "USE THIS when user asks 'my account info' or 'mening profilim'."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    # ═══════════════════════════════════════════════════════════
    # PHASE 3: PUBLIC ANONYMOUS TOOLS — No login required!
    # ═══════════════════════════════════════════════════════════
    {
        "name": "get_user_id",
        "description": (
            "Get Instagram numeric user ID from username. Works WITHOUT login. "
            "Returns user_id number. USE THIS when you need user_id for other API calls."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username (without @)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "is_public",
        "description": (
            "Check if an Instagram account is public or private. Works WITHOUT login. "
            "Returns True/False."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "exists",
        "description": (
            "Check if an Instagram username exists. Works WITHOUT login. "
            "Returns True/False."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username to check",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_feed",
        "description": (
            "Get user's feed posts by user_id. Works WITHOUT login. "
            "Returns list of posts with likes, comments, captions. "
            "USE THIS when you already have user_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Instagram numeric user ID",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum posts to fetch (default: 12)",
                },
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "get_all_posts",
        "description": (
            "Get ALL posts for a user (deep scrape). Works WITHOUT login. "
            "Returns comprehensive list of all posts. "
            "USE THIS when user wants ALL posts, not just recent ones."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum posts to fetch (default: 50)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_reels",
        "description": (
            "Get a user's Instagram Reels. Works WITHOUT login. "
            "Returns list of reels with video URLs, view counts, likes. "
            "USE THIS when user asks for reels or videos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum reels to fetch (default: 12)",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_comments",
        "description": (
            "Get comments on an Instagram post. Works WITHOUT login. "
            "Returns list of comments with author, text, likes. "
            "USE THIS when user asks for comments on a post."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "shortcode": {
                    "type": "string",
                    "description": "Post shortcode (from URL: instagram.com/p/SHORTCODE/)",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum comments to fetch (default: 20)",
                },
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "get_highlights",
        "description": (
            "Get a user's Story Highlights. Works WITHOUT login. "
            "Returns list of highlight titles and cover images. "
            "USE THIS when user asks for story highlights."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_similar_accounts",
        "description": (
            "Get accounts similar to a given user. Works WITHOUT login. "
            "Returns list of similar accounts with profile info. "
            "USE THIS when user asks 'find similar accounts' or 'accounts like X'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Instagram username",
                },
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_post_by_shortcode",
        "description": (
            "Get full post data by shortcode. Works WITHOUT login. "
            "Returns complete post with media, caption, likes, comments. "
            "USE THIS when user provides a post shortcode."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "shortcode": {
                    "type": "string",
                    "description": "Post shortcode (e.g. 'ABC123def')",
                },
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "get_post_by_url",
        "description": (
            "Get full post data from an Instagram URL. Works WITHOUT login. "
            "Returns complete post with media URLs, caption, engagement. "
            "USE THIS when user provides a full Instagram URL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full Instagram post/reel URL",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "get_media_urls",
        "description": (
            "Get direct media download URLs for a post. Works WITHOUT login. "
            "Returns image/video URLs that can be downloaded. "
            "USE THIS when user wants to download or view media from a post."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "shortcode": {
                    "type": "string",
                    "description": "Post shortcode",
                },
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "get_hashtag_posts",
        "description": (
            "Get posts for a hashtag. Works WITHOUT login. "
            "Returns list of posts tagged with the hashtag. "
            "USE THIS when user asks 'show posts with #hashtag'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {
                    "type": "string",
                    "description": "Hashtag name (without #)",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum posts to fetch (default: 10)",
                },
            },
            "required": ["hashtag"],
        },
    },
    {
        "name": "get_location_posts",
        "description": (
            "Get posts from a specific location. Works WITHOUT login. "
            "Returns list of posts tagged at the location. "
            "USE THIS when user asks about posts from a location."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "string",
                    "description": "Instagram location ID",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum posts to fetch (default: 10)",
                },
            },
            "required": ["location_id"],
        },
    },
    {
        "name": "run_diagnostics",
        "description": (
            "Run API diagnostics to test all InstaHarvest v2 methods. "
            "Tests 41 methods (sync+async) and reports success/failure. "
            "USE THIS when user asks to check API health or run diagnostics."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Test username (default: 'cristiano')",
                },
            },
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Upload & Content Creation (7 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "upload_photo",
        "description": "Upload a photo post to Instagram. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"},
                "caption": {"type": "string", "description": "Post caption text"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "upload_video",
        "description": "Upload a video post to Instagram. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to video file"},
                "caption": {"type": "string", "description": "Post caption text"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "upload_reel",
        "description": "Upload a reel (short video) to Instagram. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to video file"},
                "caption": {"type": "string", "description": "Reel caption text"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "upload_story_photo",
        "description": "Upload a photo story. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to image file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "upload_story_video",
        "description": "Upload a video story. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to video file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "upload_carousel",
        "description": "Upload a carousel (multiple photos/videos) post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}, "description": "Array of file paths"},
                "caption": {"type": "string", "description": "Post caption text"},
            },
            "required": ["paths"],
        },
    },
    {
        "name": "delete_media",
        "description": "Delete a media post by its ID. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID to delete"},
            },
            "required": ["media_id"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Advanced Media (6 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_likers",
        "description": "Get users who liked a specific post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID or URL"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "save_media",
        "description": "Save/bookmark a post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID or URL"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "unsave_media",
        "description": "Remove a post from saved/bookmarks. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID or URL"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "get_comment_replies",
        "description": "Get replies to a specific comment. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID"},
                "comment_id": {"type": "string", "description": "Comment ID"},
            },
            "required": ["media_id", "comment_id"],
        },
    },
    {
        "name": "reply_to_comment",
        "description": "Reply to a comment on a post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID"},
                "comment_id": {"type": "string", "description": "Comment ID to reply to"},
                "text": {"type": "string", "description": "Reply text"},
            },
            "required": ["media_id", "comment_id", "text"],
        },
    },
    {
        "name": "edit_caption",
        "description": "Edit the caption of a post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID"},
                "caption": {"type": "string", "description": "New caption text"},
            },
            "required": ["media_id"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Advanced Friendships (8 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "block_user",
        "description": "Block a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to block"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "unblock_user",
        "description": "Unblock a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to unblock"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "mute_user",
        "description": "Mute a user (hide posts/stories). REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to mute"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "unmute_user",
        "description": "Unmute a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to unmute"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "remove_follower",
        "description": "Remove a follower from your account. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to remove"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_pending_requests",
        "description": "Get pending follow requests. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_request",
        "description": "Approve a pending follow request. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to approve"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_mutual_followers",
        "description": "Get mutual followers between you and another user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to check mutuals with"},
            },
            "required": ["username"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Stories Management (4 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_story_viewers",
        "description": "Get viewers of your story. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Story media ID"},
            },
            "required": ["story_id"],
        },
    },
    {
        "name": "react_to_story",
        "description": "React to a story with an emoji. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "story_id": {"type": "string", "description": "Story media ID"},
                "emoji": {"type": "string", "description": "Emoji to react with (default: ❤️)"},
            },
            "required": ["story_id"],
        },
    },
    {
        "name": "create_highlight",
        "description": "Create a story highlight collection. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Highlight title"},
                "story_ids": {"type": "array", "items": {"type": "string"}, "description": "Array of story IDs"},
            },
            "required": ["title", "story_ids"],
        },
    },
    {
        "name": "get_all_highlights",
        "description": "Get all highlights with their items for a user.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
            },
            "required": ["username"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Growth (4 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_non_followers",
        "description": "Get users you follow who DON'T follow you back. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_fans",
        "description": "Get fans — users who follow you but you DON'T follow back. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "unfollow_non_followers",
        "description": "Unfollow users who don't follow you back. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max users to unfollow (default: 10)"},
            },
        },
    },
    {
        "name": "follow_hashtag_users",
        "description": "Follow users who posted with a specific hashtag. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {"type": "string", "description": "Hashtag to target (without #)"},
                "max_count": {"type": "integer", "description": "Max users to follow (default: 5)"},
            },
            "required": ["hashtag"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Export & Pipeline (6 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "export_followers_csv",
        "description": "Export a user's followers list to CSV file. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "filename": {"type": "string", "description": "Output CSV filename"},
                "max_count": {"type": "integer", "description": "Max followers to export"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "export_following_csv",
        "description": "Export a user's following list to CSV file. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "filename": {"type": "string", "description": "Output CSV filename"},
                "max_count": {"type": "integer", "description": "Max following to export"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "export_post_likers",
        "description": "Export likers of a post to file. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media ID"},
                "filename": {"type": "string", "description": "Output filename"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "export_to_json",
        "description": "Export data to a JSON file.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to export"},
                "filename": {"type": "string", "description": "Output JSON filename"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "save_to_sqlite",
        "description": "Save data to a SQLite database.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to save"},
                "db_name": {"type": "string", "description": "SQLite database filename"},
                "table_name": {"type": "string", "description": "Table name"},
            },
            "required": ["data"],
        },
    },
    {
        "name": "save_to_jsonl",
        "description": "Save data to JSONL (JSON Lines) format file.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to save"},
                "filename": {"type": "string", "description": "Output JSONL filename"},
            },
            "required": ["data"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Location (3 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "search_locations",
        "description": "Search Instagram locations by name/query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Location name to search (e.g. 'Tashkent')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_location_info",
        "description": "Get location details by location ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {"type": "string", "description": "Instagram location ID"},
            },
            "required": ["location_id"],
        },
    },
    {
        "name": "get_nearby_locations",
        "description": "Find nearby Instagram locations by GPS coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lng": {"type": "number", "description": "Longitude"},
            },
            "required": ["lat", "lng"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Feed (3 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_timeline",
        "description": "Get your home timeline/feed posts. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max posts to fetch (default: 10)"},
            },
        },
    },
    {
        "name": "get_saved_posts",
        "description": "Get your saved/bookmarked posts. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max posts to fetch (default: 10)"},
            },
        },
    },
    {
        "name": "get_liked_posts",
        "description": "Get posts you have liked. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max posts to fetch (default: 10)"},
            },
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Users (2 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_full_profile",
        "description": "Get comprehensive profile data for a user (uses login API if logged in, public API otherwise).",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "parse_bio",
        "description": "Parse a user's bio for emails, phone numbers, URLs, hashtags, and mentions.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
            },
            "required": ["username"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Hashtag Research (2 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "analyze_hashtag",
        "description": "Analyze a hashtag — post count, engagement level, competition. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {"type": "string", "description": "Hashtag to analyze (without #)"},
            },
            "required": ["hashtag"],
        },
    },
    {
        "name": "suggest_hashtags",
        "description": "Suggest related hashtags for a given hashtag or topic. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {"type": "string", "description": "Base hashtag (without #)"},
            },
            "required": ["hashtag"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Notifications (2 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "get_notifications",
        "description": "Get recent notifications/activity (likes, comments, follows). REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_activity_counts",
        "description": "Get activity count summary. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Public Data Analytics (3 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "compare_profiles",
        "description": "Compare two or more Instagram profiles side by side. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "usernames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of usernames to compare (at least 2)",
                },
            },
            "required": ["usernames"],
        },
    },
    {
        "name": "engagement_analysis",
        "description": "Analyze engagement rate and metrics for a user. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username to analyze"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "build_report",
        "description": "Build a comprehensive analytics report for a user. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
            },
            "required": ["username"],
        },
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Advanced Search (3 tools)
    # ═══════════════════════════════════════════════════
    {
        "name": "search_hashtags",
        "description": "Search for hashtags by keyword query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Hashtag search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_places",
        "description": "Search for places/locations on Instagram.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Place/location name to search"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "explore_feed",
        "description": "Get Instagram Explore page content. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max items to fetch (default: 10)"},
            },
        },
    },

    # ═══════════════════════════════════════════════════
    # SYSTEM UTILITY TOOLS (17 tools)
    # ═══════════════════════════════════════════════════

    # ── File I/O (7 tools) ─────────────────────────────
    {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories automatically. Supports absolute and relative paths.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path (absolute or relative)"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "append_to_file",
        "description": "Append content to an existing file (creates it if not exists).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to append"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "copy_file",
        "description": "Copy a file from source to destination.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path"},
                "destination": {"type": "string", "description": "Destination file path"},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "move_file",
        "description": "Move or rename a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path"},
                "destination": {"type": "string", "description": "Destination file path"},
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file or empty directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to delete"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "file_exists",
        "description": "Check if a file or directory exists at the given path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to check"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_file_info",
        "description": "Get detailed file information: size, type, timestamps.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File or directory path"},
            },
            "required": ["path"],
        },
    },

    # ── Directory Operations (4 tools) ─────────────────
    {
        "name": "get_working_directory",
        "description": "Get the current working directory and its contents.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "create_directory",
        "description": "Create a directory (including parent directories).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to create"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_directory",
        "description": "List directory contents with details (size, type). Supports patterns and recursive listing.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: current dir)"},
                "pattern": {"type": "string", "description": "Glob pattern filter (e.g. '*.json', '*.py')"},
                "recursive": {"type": "boolean", "description": "Search recursively (default: false)"},
                "max_items": {"type": "integer", "description": "Max items to list (default: 50)"},
            },
        },
    },
    {
        "name": "find_files",
        "description": "Search for files by glob pattern (recursive). Examples: '*.json', '**/*.py', 'data_*'.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.csv', 'report*.json')"},
                "directory": {"type": "string", "description": "Starting directory (default: current dir)"},
                "max_results": {"type": "integer", "description": "Max results (default: 30)"},
            },
            "required": ["pattern"],
        },
    },

    # ── Session & Data Persistence (3 tools) ───────────
    {
        "name": "save_session_data",
        "description": "Save JSON data to a named session for later retrieval. Use to persist configs, lists, tokens, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Session name (e.g. 'target_accounts', 'config', 'login_data')"},
                "data": {"type": "string", "description": "JSON data to save"},
            },
            "required": ["name", "data"],
        },
    },
    {
        "name": "load_session_data",
        "description": "Load previously saved session data by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Session name to load"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_sessions",
        "description": "List all saved session files with sizes and dates.",
        "parameters": {"type": "object", "properties": {}},
    },

    # ── Environment & System (3 tools) ─────────────────
    {
        "name": "get_env_var",
        "description": "Read an environment variable value.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Environment variable name (e.g. 'HOME', 'USERPROFILE', 'PATH')"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "set_working_directory",
        "description": "Change the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to switch to"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_system_info",
        "description": "Get system information: OS, Python version, working directory, disk space, saved sessions count.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ═══════════════════════════════════════════════════════════
    # PHASE 5: Auth, Analytics, Automation, Pipeline (47 tools)
    # ═══════════════════════════════════════════════════════════
    # ── Auth ──────────────────────────────────────────────
    {
        "name": "login",
        "description": "Login to Instagram with username and password. Supports 2FA.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "password": {"type": "string", "description": "Instagram password"},
            },
            "required": ["username", "password"],
        },
    },
    {
        "name": "validate_session",
        "description": "Check if current session is still valid. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "logout",
        "description": "Logout from Instagram and invalidate session. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ── Analytics ─────────────────────────────────────────
    {
        "name": "get_engagement_rate",
        "description": "Calculate engagement rate for a user based on recent posts. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "post_count": {"type": "integer", "description": "Number of posts to analyze (default: 12)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_best_posting_times",
        "description": "Analyze best times to post based on engagement patterns. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "post_count": {"type": "integer", "description": "Number of posts to analyze (default: 30)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_content_analysis",
        "description": "Analyze content types (photo/video/carousel) and their performance. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "post_count": {"type": "integer", "description": "Number of posts to analyze (default: 20)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_profile_summary",
        "description": "Get comprehensive profile summary with analytics data. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "post_count": {"type": "integer", "description": "Number of posts to include (default: 12)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "compare_accounts",
        "description": "Compare multiple Instagram accounts side by side. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "usernames": {"type": "array", "items": {"type": "string"}, "description": "List of usernames to compare (min 2)"},
                "post_count": {"type": "integer", "description": "Posts per account to analyze (default: 12)"},
            },
            "required": ["usernames"],
        },
    },
    # ── Insights ──────────────────────────────────────────
    {
        "name": "get_account_insights",
        "description": "Get account insights summary (reach, impressions, profile views). REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_media_insight",
        "description": "Get insights for a specific media (reach, saves, shares). REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media PK/ID"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "get_business_info",
        "description": "Get business account info (category, contact, address). REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Instagram user ID"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "get_ads_accounts",
        "description": "Get linked Facebook Ads accounts. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ── Audience ──────────────────────────────────────────
    {
        "name": "find_lookalike_audience",
        "description": "Find users similar to a target account's followers. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Target username"},
                "max_count": {"type": "integer", "description": "Max results (default: 50)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "get_audience_overlap",
        "description": "Calculate follower overlap between two accounts. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username_a": {"type": "string", "description": "First username"},
                "username_b": {"type": "string", "description": "Second username"},
            },
            "required": ["username_a", "username_b"],
        },
    },
    {
        "name": "get_audience_insights",
        "description": "Get audience demographics and behavior insights. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
            },
            "required": ["username"],
        },
    },
    # ── A/B Testing ───────────────────────────────────────
    {
        "name": "create_ab_test",
        "description": "Create a new A/B test with variants. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "variants": {"type": "array", "items": {"type": "string"}, "description": "Test variant names/descriptions"},
                "metric": {"type": "string", "description": "Metric to optimize (default: 'engagement')"},
                "description": {"type": "string", "description": "Test description"},
            },
            "required": ["variants"],
        },
    },
    {
        "name": "run_ab_test",
        "description": "Execute an A/B test. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "test_id": {"type": "string", "description": "Test ID to run"},
            },
            "required": ["test_id"],
        },
    },
    {
        "name": "get_ab_results",
        "description": "Get A/B test results and winner. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "test_id": {"type": "string", "description": "Test ID"},
            },
            "required": ["test_id"],
        },
    },
    {
        "name": "list_ab_tests",
        "description": "List all A/B tests with status. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (optional)"},
            },
        },
    },
    # ── Automation ────────────────────────────────────────
    {
        "name": "auto_dm_new_followers",
        "description": "Auto-send DM to new followers with a custom message. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message text to send"},
                "max_count": {"type": "integer", "description": "Max followers to DM (default: 10)"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "auto_comment_hashtag",
        "description": "Auto-comment on posts from a hashtag. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {"type": "string", "description": "Hashtag name (without #)"},
                "comment": {"type": "string", "description": "Comment text"},
                "max_count": {"type": "integer", "description": "Max posts to comment (default: 5)"},
            },
            "required": ["hashtag", "comment"],
        },
    },
    {
        "name": "auto_like_feed",
        "description": "Auto-like posts from your timeline feed. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max posts to like (default: 10)"},
            },
        },
    },
    {
        "name": "auto_like_hashtag",
        "description": "Auto-like posts from a hashtag. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "hashtag": {"type": "string", "description": "Hashtag name (without #)"},
                "max_count": {"type": "integer", "description": "Max posts to like (default: 10)"},
            },
            "required": ["hashtag"],
        },
    },
    {
        "name": "auto_watch_stories",
        "description": "Auto-watch stories from your following list. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_count": {"type": "integer", "description": "Max stories to watch (default: 20)"},
            },
        },
    },
    {
        "name": "get_action_log",
        "description": "Get automation action log — history of all automated actions. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ── Scheduler ─────────────────────────────────────────
    {
        "name": "schedule_post",
        "description": "Schedule a photo post for later. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to image file"},
                "caption": {"type": "string", "description": "Post caption"},
                "schedule_time": {"type": "string", "description": "ISO datetime or relative time (e.g. '2024-01-15 10:00', 'in 2 hours')"},
            },
            "required": ["image_path", "schedule_time"],
        },
    },
    {
        "name": "schedule_story",
        "description": "Schedule a story for later. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_path": {"type": "string", "description": "Path to photo/video file"},
                "schedule_time": {"type": "string", "description": "When to post"},
            },
            "required": ["media_path", "schedule_time"],
        },
    },
    {
        "name": "schedule_reel",
        "description": "Schedule a reel for later. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to video file"},
                "caption": {"type": "string", "description": "Reel caption"},
                "schedule_time": {"type": "string", "description": "When to post"},
            },
            "required": ["video_path", "schedule_time"],
        },
    },
    {
        "name": "list_scheduled_jobs",
        "description": "List all scheduled jobs (pending, done, cancelled). REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "cancel_scheduled_job",
        "description": "Cancel a scheduled job by ID. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID to cancel"},
            },
            "required": ["job_id"],
        },
    },
    # ── Monitor ───────────────────────────────────────────
    {
        "name": "monitor_account",
        "description": "Start monitoring an account for changes (new posts, follower changes, bio updates). REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to monitor"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "unmonitor_account",
        "description": "Stop monitoring an account. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username to stop monitoring"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "monitor_check_now",
        "description": "Force check all monitored accounts for changes right now. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_monitor_events",
        "description": "Get monitoring event log — all detected changes. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Filter by username (optional)"},
            },
        },
    },
    {
        "name": "get_monitor_stats",
        "description": "Get monitoring statistics — watched accounts, event counts. REQUIRES LOGIN.",
        "parameters": {"type": "object", "properties": {}},
    },
    # ── Pipeline ──────────────────────────────────────────
    {
        "name": "pipeline_to_sqlite",
        "description": "Export user data to SQLite database via pipeline. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "db_path": {"type": "string", "description": "SQLite database path (default: pipeline.db)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "pipeline_to_jsonl",
        "description": "Export user data to JSONL file via pipeline. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "output_path": {"type": "string", "description": "Output file path (default: pipeline.jsonl)"},
            },
            "required": ["username"],
        },
    },
    # ── Bulk Download ─────────────────────────────────────
    {
        "name": "bulk_download_posts",
        "description": "Download ALL posts (photos/videos) from a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "output_dir": {"type": "string", "description": "Output directory (default: downloads)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "bulk_download_stories",
        "description": "Download ALL current stories from a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "output_dir": {"type": "string", "description": "Output directory (default: downloads)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "bulk_download_highlights",
        "description": "Download ALL highlights from a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "output_dir": {"type": "string", "description": "Output directory (default: downloads)"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "bulk_download_everything",
        "description": "Download EVERYTHING (posts, stories, highlights) from a user. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Instagram username"},
                "output_dir": {"type": "string", "description": "Output directory (default: downloads)"},
            },
            "required": ["username"],
        },
    },
    # ── AI Suggest ────────────────────────────────────────
    {
        "name": "ai_suggest_hashtags",
        "description": "AI-powered hashtag suggestions based on caption text. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "caption": {"type": "string", "description": "Caption text to analyze"},
            },
            "required": ["caption"],
        },
    },
    {
        "name": "ai_suggest_captions",
        "description": "AI-powered caption ideas for a topic. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic or theme"},
                "style": {"type": "string", "description": "Caption style (e.g. 'funny', 'professional', 'motivational')"},
            },
            "required": ["topic"],
        },
    },
    # ── Comment Manager ───────────────────────────────────
    {
        "name": "manage_comments",
        "description": "Get and filter comments on a post with advanced options. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media PK/ID"},
                "max_count": {"type": "integer", "description": "Max comments (default: 50)"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "auto_reply_comments",
        "description": "Auto-reply to comments on a post with a custom message. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media PK/ID"},
                "reply": {"type": "string", "description": "Reply text"},
                "max_count": {"type": "integer", "description": "Max comments to reply to (default: 10)"},
            },
            "required": ["media_id", "reply"],
        },
    },
    {
        "name": "delete_spam_comments",
        "description": "Auto-detect and delete spam comments on a post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media PK/ID"},
            },
            "required": ["media_id"],
        },
    },
    {
        "name": "get_comment_sentiment",
        "description": "Analyze sentiment (positive/negative/neutral) of comments on a post. REQUIRES LOGIN.",
        "parameters": {
            "type": "object",
            "properties": {
                "media_id": {"type": "string", "description": "Media PK/ID"},
            },
            "required": ["media_id"],
        },
    },
    # ═══════════════════════════════════════════════════════════
    # UTILITY TOOLS (7 tools)
    # ═══════════════════════════════════════════════════════════
    {
        "name": "json_parse",
        "description": "Parse raw JSON string and return pretty-printed output. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Raw JSON string to parse"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "csv_to_json",
        "description": "Convert CSV file to JSON array. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to CSV file"},
                "delimiter": {"type": "string", "description": "Column delimiter (default: ',')"},
                "max_rows": {"type": "integer", "description": "Max rows to read (default: 500)"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "json_to_csv",
        "description": "Convert JSON array data to CSV file. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON array string of objects"},
                "path": {"type": "string", "description": "Output CSV file path"},
            },
            "required": ["data", "path"],
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate a math expression safely. Supports sqrt, sin, cos, log, pi, factorial, etc. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression (e.g. 'sqrt(144) + pi', '2**10', 'factorial(5)')"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "text_replace",
        "description": "Find and replace text in a file. Supports regex. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "find": {"type": "string", "description": "Text or regex pattern to find"},
                "replace": {"type": "string", "description": "Replacement text"},
                "regex": {"type": "boolean", "description": "Use regex matching (default: false)"},
            },
            "required": ["path", "find", "replace"],
        },
    },
    {
        "name": "merge_files",
        "description": "Merge multiple text files into one. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to merge"},
                "output": {"type": "string", "description": "Output file path"},
                "separator": {"type": "string", "description": "Separator between files (default: newline)"},
            },
            "required": ["files", "output"],
        },
    },
    {
        "name": "download_url",
        "description": "Download a file from URL to local path. Works WITHOUT login.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to download from"},
                "path": {"type": "string", "description": "Local file path to save to (auto-named if omitted)"},
            },
            "required": ["url"],
        },
    },
]


class BaseProvider(ABC):
    """
    Abstract AI provider interface.

    All AI providers must implement:
        - generate(): send messages and get response with optional tool calls
    """

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self._total_tokens = 0

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1,
    ) -> ProviderResponse:
        """
        Generate AI response.

        Args:
            messages: Chat history [{role, content}, ...]
            tools: Tool definitions (default: instaharvest_v2_TOOLS)
            temperature: Creativity (0=precise, 1=creative)

        Returns:
            ProviderResponse with content and/or tool_calls
        """
        ...

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name for logging."""
        ...

    def format_tools(self, tools: Optional[List[Dict]] = None) -> List[Dict]:
        """Get tools in provider-specific format. Override if needed."""
        return tools or instaharvest_v2_TOOLS
