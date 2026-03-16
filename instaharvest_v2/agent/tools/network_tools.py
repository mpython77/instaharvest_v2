"""
Network Tools
=============
HTTP request, web search, and DM handlers.
"""

import re
import urllib.parse
import urllib.request
import urllib.error
import logging
from typing import Dict

logger = logging.getLogger("instaharvest_v2.agent.tools")


def handle_http_request(args: Dict) -> str:
    """Make HTTP request."""
    method = args.get("method", "GET").upper()
    url = args.get("url", "")
    headers = args.get("headers", {})
    body = args.get("body", "")

    if not url:
        return "Error: no URL provided"

    if method not in ("GET", "POST"):
        return f"Error: unsupported method '{method}'. Use GET or POST"

    # Security: block localhost and internal IPs
    blocked = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.", "10.", "192.168.", "172.16."]
    for pattern in blocked:
        if pattern in url.lower():
            return f"Error: requests to internal/local addresses are blocked"

    try:
        req = urllib.request.Request(url, method=method)

        # Set headers
        req.add_header("User-Agent", "InstaHarvest v2-Agent/1.0")
        for key, val in headers.items():
            req.add_header(key, val)

        # Set body for POST
        data = body.encode("utf-8") if body and method == "POST" else None

        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            response_body = resp.read().decode("utf-8", errors="replace")
            status = resp.status

            # Truncate large responses
            if len(response_body) > 5000:
                response_body = response_body[:5000] + "\n... (truncated)"

            return f"HTTP {status}\n{response_body}"

    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}"
    except Exception as e:
        return f"Request error: {e}"


def handle_search_web(args: Dict) -> str:
    """Search the web using DuckDuckGo Lite."""
    query = args.get("query", "")

    if not query:
        return "Error: no search query provided"

    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InstaHarvest v2-Agent/1.0")

        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract text snippets from HTML
        results = _extract_search_results(html)

        if not results:
            return f"No results found for: '{query}'"

        lines = [f"🔍 Search results for: '{query}'"]
        lines.append("-" * 50)

        for i, result in enumerate(results[:5], 1):
            lines.append(f"\n  {i}. {result['title']}")
            if result.get("snippet"):
                lines.append(f"     {result['snippet'][:200]}")
            if result.get("url"):
                lines.append(f"     → {result['url']}")

        return "\n".join(lines)

    except Exception as e:
        return f"Search error: {e}"


def _extract_search_results(html: str) -> list:
    """Extract search results from DuckDuckGo Lite HTML."""
    results = []

    # Find result links and snippets
    title_pattern = re.compile(r'<a[^>]*class="result-link"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    snippet_pattern = re.compile(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', re.DOTALL)

    titles = title_pattern.findall(html)
    snippets = snippet_pattern.findall(html)

    # Fallback: simpler patterns
    if not titles:
        titles = re.findall(r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)

    if not snippets:
        snippets = re.findall(r'<td[^>]*class="(?:result-snippet|snippet)"[^>]*>(.*?)</td>', html, re.DOTALL)

    for i, (url, title) in enumerate(titles[:10]):
        # Clean HTML tags
        clean_title = re.sub(r'<[^>]+>', '', title).strip()
        clean_snippet = ""
        if i < len(snippets):
            clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

        if clean_title:
            results.append({
                "title": clean_title,
                "url": url,
                "snippet": clean_snippet,
            })

    return results


def handle_send_dm(args: Dict, ig=None, is_logged_in=False) -> str:
    """Send a direct message."""
    username = args.get("username", "").strip().lstrip("@").lower()
    text = args.get("text", "").strip()
    thread_id = args.get("thread_id", "").strip()

    if not text:
        return "Error: message text is required."
    if not is_logged_in:
        return "Error: sending DM requires login."
    if ig is None:
        return "Error: Instagram client not available."

    try:
        # If thread_id is given, send directly
        if thread_id:
            ig.direct.send_text(thread_id, text)
            return f"✅ Message sent to thread {thread_id}: '{text}'"

        # Otherwise, need username to create/find thread
        if not username:
            return "Error: either username or thread_id is required."

        user = ig.users.get_by_username(username)
        if not user:
            return f"User '@{username}' not found."

        user_pk = user.get("pk") if isinstance(user, dict) else getattr(user, "pk", None)
        if not user_pk:
            return f"Could not get user ID for '@{username}'."

        # Create new thread with message
        result = ig.direct.create_thread([user_pk], text=text)
        return f"✅ Message sent to @{username}: '{text}'"

    except Exception as e:
        return f"Error sending DM: {e}"


# ═══════════════════════════════════════════════════════════
# PHASE 4: ADVANCED SEARCH (3 tools)
# ═══════════════════════════════════════════════════════════

def handle_search_hashtags(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Search for hashtags by query."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        results = ig.search.search_hashtags(query)
        if not results:
            return f"No hashtags found for '{query}'."
        items = results if isinstance(results, list) else [results]
        lines = [f"#️⃣ Hashtag search: '{query}' ({len(items)} found):"]
        for i, h in enumerate(items[:15], 1):
            if isinstance(h, dict):
                name = h.get("name", h.get("hashtag", "?"))
                count = h.get("media_count", h.get("count", 0))
                lines.append(f"  {i}. #{name} ({count:,} posts)" if count else f"  {i}. #{name}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching hashtags: {e}"


def handle_search_places(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Search for places/locations on Instagram."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: 'query' is required."
    if ig is None:
        return "Error: Instagram client not available."
    try:
        results = ig.search.search_places(query)
        if not results:
            return f"No places found for '{query}'."
        items = results if isinstance(results, list) else [results]
        lines = [f"📍 Places search: '{query}' ({len(items)} found):"]
        for i, p in enumerate(items[:10], 1):
            if isinstance(p, dict):
                name = p.get("title", p.get("name", "?"))
                loc_id = p.get("location", {}).get("pk", "?") if isinstance(p.get("location"), dict) else "?"
                address = p.get("subtitle", p.get("address", ""))
                lines.append(f"  {i}. {name} (ID: {loc_id}) {address}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching places: {e}"


def handle_explore_feed(args: Dict, ig=None, is_logged_in=False, **kw) -> str:
    """Get Instagram Explore feed content."""
    if not is_logged_in:
        return "❌ Login required to view Explore feed."
    max_count = min(args.get("max_count", 10), 30)
    try:
        results = ig.search.explore(max_count=max_count)
        if not results:
            return "No explore content found."
        items = results if isinstance(results, list) else [results]
        lines = [f"🔍 Explore Feed ({len(items)} items):"]
        for i, p in enumerate(items[:max_count], 1):
            if isinstance(p, dict):
                user = p.get("user", {}).get("username", "?") if isinstance(p.get("user"), dict) else "?"
                likes = p.get("like_count", 0)
                sc = p.get("shortcode", p.get("code", ""))
                lines.append(f"  {i}. @{user} ❤️{likes:,} https://instagram.com/p/{sc}/")
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting explore feed: {e}"

