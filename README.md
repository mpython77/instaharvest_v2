# 📸 InstaHarvest v2

**Python Instagram Private & Public API Client** — sync/async parity, anti-detection, Pydantic models, AI Agent

[![PyPI](https://img.shields.io/pypi/v/instaharvest-v2?color=blue)](https://pypi.org/project/instaharvest-v2/)
[![Python](https://img.shields.io/pypi/pyversions/instaharvest-v2)](https://pypi.org/project/instaharvest-v2/)
[![License](https://img.shields.io/github/license/mpython77/instaharvest_v2)](https://github.com/mpython77/instaharvest_v2/blob/main/LICENSE)
![Modules](https://img.shields.io/badge/modules-33+34-green)
![Async](https://img.shields.io/badge/async-full_parity-brightgreen)
![Agent Tools](https://img.shields.io/badge/agent_tools-162-orange)
![Tests](https://img.shields.io/badge/tests-6292_passed-success)
![Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen)
[![Docs](https://img.shields.io/badge/docs-online-blue?logo=readthedocs)](https://mpython77.github.io/instaharvest_v2/)

> 33 sync + 34 async modules (33 async API mirrors + `batch`) • 335+ methods • 162 agent tools • Pydantic v2 models • AI Agent • CI/CD

---

## Architecture Overview

- **Multi-Strategy Fallback**: Automatically rotates between `GraphQL`, `Mobile API`, and `Web API` endpoints when an endpoint fails or returns incomplete data.
- **Rotating Proxy Auto-Detection**: `ProxyManager.detect_proxy_type()` identifies rotating-IP proxies and pairs with Mobile API pagination to avoid strict GraphQL cookie checks. See `examples/parallel_proxy_mobile.py`.
- **TLS/JA3 Impersonation**: Uses `curl_cffi` to match coherent Chrome TLS/header profiles (`chrome142`/`chrome136`) with session-locked identities.
- **Anonymous Public Access**: Supports unauthenticated profile, post, reel, comment, hashtag, and location lookups via `Instagram.anonymous()` and `AsyncInstagram.anonymous()`.
- **Pydantic v2 Models**: Typed return objects (`InstaModel` with `extra="allow"`) supporting both attribute access and dict-style indexing without breaking when upstream API payloads change.

---

## Installation

```bash
pip install instaharvest-v2
```

**With extras:**

```bash
pip install instaharvest-v2[dev]      # pytest, pytest-cov, pytest-asyncio
pip install instaharvest-v2[agent]    # AI providers (Gemini, OpenAI, Claude)
pip install instaharvest-v2[web]      # FastAPI web playground
pip install instaharvest-v2[all]      # everything
```

---

## Quick Start

### With cookies (.env file)

```python
from instaharvest_v2 import Instagram

ig = Instagram.from_env(".env")
user = ig.users.get_by_username("cristiano")
print(user.username)        # cristiano
print(user.followers)       # 650000000
print(user["biography"])    # dict-like access works too
```

### With login

```python
ig = Instagram()
ig.login("username", "password")
ig.auth.save_session("session.json")   # save for next time
```

### Load saved session

```python
ig = Instagram()
ig.auth.load_session("session.json")   # no re-login needed
```

### Async mode (concurrent bulk requests)

```python
import asyncio
from instaharvest_v2 import AsyncInstagram

async def main():
    async with AsyncInstagram.from_env(mode="fast") as ig:
        # Parallel — all at once!
        tasks = [ig.users.get_by_username(u) for u in usernames]
        profiles = await asyncio.gather(*tasks)

asyncio.run(main())
```

### Challenge auto-resolver

```python
ig = Instagram(
    challenge_callback=lambda ctx: input(f"Code sent to {ctx.contact_point}: ")
)
# Email/SMS challenges resolved automatically!
```

### Anonymous (no login)

```python
ig = Instagram.anonymous(unlimited=True)
ig.add_proxy("http://user:pass@host:port")  # optional

profile = ig.public.get_profile("cristiano")
posts = ig.public.get_posts("cristiano", max_count=12)
reels = ig.public.get_reels("cristiano", max_count=10)
comments = ig.public.get_comments("ABC123", max_count=20)
similar = ig.public.get_similar_accounts("cristiano")
hashtag = ig.public.get_hashtag_posts("fashion", max_count=10)
location = ig.public.get_location_posts("213385402", max_count=10)
```

### 🛰️ Parallel Scraping with Rotating Proxies

When using rotating-IP proxies (such as residential backconnect pools), Instagram often rejects public GraphQL pagination with HTTP 400. Combining `ProxyManager.detect_proxy_type()` with Mobile API endpoints handles rotating IPs reliably:

```python
import asyncio
from instaharvest_v2.proxy_manager import ProxyManager
from instaharvest_v2.async_anon_client import AsyncAnonClient

async def main():
    pm = ProxyManager()
    pm.add_proxy("http://user:pass@res.proxy-seller.com:10000")
    
    # 1. Automatically detects if the proxy rotates IPs and disables strict cookie checks
    await pm.detect_proxy_type()  
    
    # 2. Control concurrency (e.g. 5) to prevent Proxy-Supplier 503 HTTP Tunnel errors
    client = AsyncAnonClient(proxy_manager=pm, unlimited=True, max_concurrency=5)
    
    # 3. Use Mobile Feed API to paginate seamlessly across all IPs!
    feed = await client.get_user_feed_mobile(user_id="173560420", count=12, max_id=None)
    
asyncio.run(main())
```

*Check out `examples/parallel_proxy_mobile.py` for a full 50-profile parallel scraping test!*

### 🔬 API Diagnostics

```python
from instaharvest_v2 import Instagram, run_diagnostics

ig = Instagram.anonymous(unlimited=True)
ig.add_proxy("http://proxy...")
results = run_diagnostics(ig, username="cristiano")  # tests all 41 methods
```

**CLI:**

```bash
python -m instaharvest_v2 diagnose cristiano --proxy http://...
python -m instaharvest_v2 diagnose cristiano --layer public --sync-only
python -m instaharvest_v2 diagnose cristiano -o ./results/  # JSON output
```

### 🎬 Reel / Post Scraping (no login, no cookies!)

```python
ig = Instagram.anonymous()

# By shortcode (from URL: instagram.com/reel/ABC123/)
post = ig.public.get_post_by_shortcode("ABC123")
print(post["likes"])         # 69603
print(post["video_url"])     # full video download URL
print(post["audio"])         # {'title': 'Original audio', 'artist': '...'}

# By full URL
post = ig.public.get_post_by_url("https://instagram.com/reel/ABC123/")

# Works for ALL types: Reels, Photos, Carousels, Videos
# Returns: video_url, display_url, likes, views, comments, audio, owner, carousel_media
```

### 🤖 AI Agent (162 built-in tools)

```python
from instaharvest_v2 import Instagram
from instaharvest_v2.agent import InstaAgent, Permission

ig = Instagram.from_env(".env")
agent = InstaAgent(
    ig=ig,
    provider="gemini",        # 11 AI providers
    permission=Permission.FULL_ACCESS,
    memory=True,
)

agent.ask("Get @cristiano's last 10 posts and save to CSV")
agent.ask("Compare @nike and @adidas engagement rates")
agent.ask("Find the best posting time for my account")
agent.ask("Show similar accounts to @nike")
agent.ask("Get comments on post ABC123")
agent.ask("Run API diagnostics for @cristiano")
```

## .env Format

```env
SESSION_ID=your_session_id
CSRF_TOKEN=your_csrf_token
DS_USER_ID=your_user_id
MID=optional
IG_DID=optional
DATR=optional
USER_AGENT=optional
```

---

## API Reference

### 👤 Users

```python
user = ig.users.get_by_username("cristiano")   # → User model
user = ig.users.get_by_id(123456789)           # → User model
users = ig.users.search("cristiano")           # → List[UserShort]
profile = ig.users.get_full_profile("cristiano")  # merged User
bio = ig.users.parse_bio(user)                 # → BioParsed
```

### 📷 Media

```python
media = ig.media.get_info(media_pk)            # → Media model
media = ig.media.get_by_shortcode("ABC123")    # → Media model
likers = ig.media.get_likers(media_pk)         # → List[UserShort]
comments = ig.media.get_comments_parsed(pk)    # → List[Comment]

ig.media.like(media_pk)
ig.media.comment(media_pk, "Nice! 🔥")
ig.media.save(media_pk)
ig.media.edit_caption(media_pk, "New caption")
ig.media.pin_comment(media_pk, comment_pk)
```

### 📰 Feed (GraphQL v2 + REST fallback)

```python
# Home feed (GraphQL v2 — fast and reliable)
timeline = ig.feed.get_timeline(count=12)     # → {posts, has_next, end_cursor}
all_tl = ig.feed.get_all_timeline(max_posts=50)  # full pagination

# User posts
ig.feed.get_user_feed(user_pk)                # REST endpoint
posts = ig.feed.get_all_posts(user_pk, max_posts=100, delay=2)

# Reels (GraphQL v2)
reels = ig.feed.get_reels_feed(count=10)      # Trending reels

# Saved/Liked/Tag
ig.feed.get_saved()                           # Saved collections
ig.feed.get_liked()                           # Liked posts
ig.feed.get_tag_feed("fashion")               # By hashtag
ig.feed.get_location_feed(location_pk)        # By location
```

### 📖 Stories

```python
ig.stories.get_reels_tray()
ig.stories.get_user_stories(user_pk)
ig.stories.mark_seen(story_pks)
ig.stories.get_highlights_tray(user_pk)
ig.stories.create_highlight("My Highlight", story_pks)
ig.stories.react_to_story(story_pk, "🔥")
```

### 🤝 Friendships

```python
ig.friendships.follow(user_pk)
ig.friendships.unfollow(user_pk)
followers = ig.friendships.get_all_followers(user_pk)  # → List[UserShort]
following = ig.friendships.get_all_following(user_pk)  # → List[UserShort]
ig.friendships.block(user_pk)
ig.friendships.remove_follower(user_pk)
ig.friendships.mute(user_pk)
ig.friendships.restrict(user_pk)
ig.friendships.add_close_friend(user_pk)
ig.friendships.get_mutual_followers(user_pk)
```

### 💬 Direct Messages

```python
ig.direct.get_inbox()
ig.direct.send_text(thread_id, "Hello!")
ig.direct.send_media_share(thread_id, media_pk)
ig.direct.create_thread([user_pk1, user_pk2])
ig.direct.send_link(thread_id, "https://example.com")
ig.direct.send_reaction(thread_id, item_id, "❤️")
```

### 📤 Upload

```python
ig.upload.post_photo("photo.jpg", caption="My post")
ig.upload.post_video("video.mp4", caption="My reel")
ig.upload.post_story_photo("story.jpg")
ig.upload.post_reel("reel.mp4", caption="Trending")
ig.upload.post_carousel(["img1.jpg", "img2.jpg"], caption="Album")
ig.upload.delete_media(media_pk)
```

### 📥 Download

```python
ig.download.download_media(media_pk)
ig.download.download_stories(user_pk)
ig.download.download_highlights(user_pk)
ig.download.download_profile_pic(username="cristiano")
ig.download.download_user_posts(user_pk, max_posts=50)
ig.download.download_by_url("https://instagram.com/p/ABC123/")
```

### 🔍 Search

```python
ig.search.top_search("query")
users = ig.search.search_users("cristiano")    # → List[UserShort]
ig.search.search_hashtags("fashion")
ig.search.search_places("New York")
```

### ⚙️ Account

```python
ig.account.get_current_user()
ig.account.edit_profile(full_name="New Name")
ig.account.set_private()
ig.account.set_public()
ig.account.get_blocked_users()
ig.account.get_login_activity()
```

### 🔐 Auth

```python
ig.login("username", "password")
ig.auth.save_session("session.json")
ig.auth.load_session("session.json")
ig.auth.validate_session()
ig.auth.logout()
```

### 🌐 Public Anonymous API (23 methods, no login!)

```python
ig = Instagram.anonymous(unlimited=True)

# Profile
ig.public.get_profile("cristiano")      # Full profile data (35+ fields)
ig.public.get_user_id("cristiano")      # → 173560420
ig.public.get_profile_pic_url("cristiano")  # HD profile pic URL
ig.public.is_public("cristiano")        # → True
ig.public.exists("cristiano")           # → True
ig.public.search("cristiano")           # Search users
ig.public.get_similar_accounts("cristiano")  # Similar accounts

# Content
ig.public.get_posts("cristiano", max_count=12)      # Recent posts
ig.public.get_all_posts("cristiano", max_count=50)   # All posts
ig.public.get_feed(user_id, max_count=12)            # Feed by user_id
ig.public.get_reels("cristiano", max_count=10)       # Reels
ig.public.get_comments("ABC123", max_count=20)       # Post comments
ig.public.get_highlights("cristiano")                 # Story highlights
ig.public.get_post_by_shortcode("ABC123")            # Single post
ig.public.get_post_by_url("https://instagram.com/p/ABC123/")
ig.public.get_media(media_id)                         # Media by ID
ig.public.get_media_urls("ABC123")                    # Download URLs

# Hashtag & Location
ig.public.get_hashtag_posts("fashion", max_count=10)
ig.public.get_hashtag_posts_v2("fashion", max_count=10)
ig.public.get_location_posts("213385402", max_count=10)

# Bulk operations
ig.public.bulk_profiles(["nike", "adidas"], workers=4)
ig.public.bulk_feeds([user_id1, user_id2], max_count=12, workers=4)
```

### More Core Modules

```python
ig.hashtags.get_info("fashion")        # Hashtag info
ig.insights.get_account_summary()      # Analytics
ig.notifications.get_activity()        # Notifications
ig.graphql.get_followers(user_pk)      # GraphQL queries
ig.location.search("New York")         # Location search
ig.collections.get_list()              # Saved collections
```

### 🔬 GraphQL API v2 (Modern doc_id Transport)

Direct access to Instagram's modern GraphQL endpoints with verified doc_ids.
All methods use POST `/graphql/query`.

```python
# 👤 Profile — mini profile info (fast and lightweight)
card = ig.graphql.get_hover_card(user_id="173560420", username="cristiano")
print(card["follower_count"])    # 650000000
print(card["biography"])         # bio text
print(card["is_verified"])       # True
print(card["mutual_followers"])  # [{username, pk, ...}]

# 🔗 Similar accounts (80+ !)
suggested = ig.graphql.get_suggested_users(user_id="173560420")
for user in suggested["users"]:
    print(f"@{user['username']} | {user['full_name']}")
# → @messi, @neymar, @ronaldo, ... (~80 similar accounts)

# 📷 User posts (GraphQL — with pagination)
data = ig.graphql.get_user_posts_v2("cristiano")
for post in data["posts"]:
    print(f"{post['shortcode']} | ❤️{post['like_count']} | {post['caption'][:50]}")

# 💬 Comments (GraphQL v2)
data = ig.graphql.get_comments_v2(media_id="3843229444966511752", count=20)
for c in data["comments"]:
    print(f"@{c['user']['username']}: {c['text'][:50]} | ❤️{c['like_count']}")

# ❤️ Like a post (mutation)
result = ig.graphql.like_media(media_id="3843229444966511752")
print(result["success"])  # True

# 📺 Home timeline (GraphQL v2 — root + pagination)
timeline = ig.graphql.get_timeline_v2(count=12)
for post in timeline["posts"]:
    print(f"@{post['user']['username']} | {post['product_type']} | ❤️{post['like_count']}")

# 🎬 Trending reels
reels = ig.graphql.get_reels_trending_v2(count=10)
for reel in reels["posts"]:
    print(f"@{reel['user']['username']} | ❤️{reel['like_count']}")

# 🔖 Saved collections
saved = ig.graphql.get_saved_v2()
for col in saved["posts"]:
    print(f"{col['collection_name']} | {col['media_count']} items")
```

**Key doc_ids (16 documented of 36 registered):**

| Key | Endpoint | Status |
| ----- | ---------- | -------- |
| `profile_posts` | User posts pagination | ✅ Verified |
| `profile_reels` | User reels tab | ✅ Verified |
| `profile_tagged` | User tagged posts | ✅ Verified |
| `profile_hover_card` | Mini profile popup | ✅ Verified |
| `profile_highlights` | Story highlights tray | ✅ Verified |
| `profile_suggested` | Similar accounts | ✅ Verified |
| `feed_timeline` | Home feed (initial) | ✅ Verified |
| `feed_timeline_pagination` | Home feed (scroll) | ✅ Verified |
| `feed_reels_trending` | Trending reels | ✅ Verified |
| `feed_saved` | Saved collections | ✅ Verified |
| `media_comments` | Post comments | ✅ Verified |
| `like_media` | Like mutation | ✅ Verified |
| `stories_seen` | Story seen mutation | ✅ Verified |
| `search_null_state` | Search initial state | ✅ Verified |
| `feed_liked` | Liked posts | REST fallback |
| `feed_tag` | Hashtag feed | REST fallback |

---

## 🛠️ Advanced Tools

### 📊 Analytics

```python
report = ig.analytics.engagement_rate("cristiano")
times = ig.analytics.best_posting_times("nike")
analysis = ig.analytics.content_analysis("adidas")
summary = ig.analytics.profile_summary("messi")
result = ig.analytics.compare(["nike", "adidas", "puma"])
```

### 📤 Export (CSV / JSON)

```python
ig.export.followers_to_csv("nike", "followers.csv", max_count=5000)
ig.export.following_to_csv("nike", "following.csv")
ig.export.post_likers("media_pk", "likers.csv")
ig.export.to_json("cristiano", "profile.json", include_posts=True)
```

### 🌱 Growth Engine

```python
ig.growth.follow_users_of("competitor", count=20)
ig.growth.unfollow_non_followers(max_count=50)
non_followers = ig.growth.get_non_followers()
fans = ig.growth.get_fans()
ig.growth.add_whitelist(["friend1", "friend2"])
```

### 🤖 Automation

```python
ig.automation.comment_on_hashtag("fashion", templates=["Nice! 🔥", "Love it! ❤️"])
ig.automation.auto_like_feed(count=20)
ig.automation.auto_like_hashtag("travel", count=30)
ig.automation.watch_stories("target_user")
```

### 📅 Scheduler

```python
ig.scheduler.post_at("2026-03-01 09:00", photo="post.jpg", caption="Scheduled!")
ig.scheduler.story_at("2026-03-01 12:00", photo="story.jpg")
ig.scheduler.reel_at("2026-03-01 18:00", video="reel.mp4", caption="Reel time!")
ig.scheduler.start()  # Background worker
```

### 👁️ Account Monitor

```python
watcher = ig.monitor.watch("cristiano")
watcher.on_new_post(lambda data: print("New post!"))
watcher.on_follower_change(lambda old, new: print(f"{old} → {new}"))
watcher.on_bio_change(lambda old, new: print(f"Bio changed!"))
ig.monitor.start(interval=300)  # Check every 5 min
```

### 📥 Bulk Download

```python
ig.bulk_download.all_posts("cristiano", output_dir="./downloads")
ig.bulk_download.all_stories("cristiano", output_dir="./downloads")
ig.bulk_download.everything("cristiano", output_dir="./downloads")
```

### 🔬 Hashtag Research

```python
analysis = ig.hashtag_research.analyze("python")
related = ig.hashtag_research.related("python", count=30)
suggestions = ig.hashtag_research.suggest("coding", count=20, mix="balanced")
comparison = ig.hashtag_research.compare(["python", "javascript", "rust"])
```

### 🗃️ Data Pipeline (SQLite / JSONL)

```python
ig.pipeline.to_sqlite("cristiano", "data.db", include_posts=True, include_followers=True)
ig.pipeline.to_jsonl("cristiano", "data.jsonl", max_posts=100)
```

### 🧠 AI Hashtag Suggester

```python
result = ig.ai_suggest.hashtags_from_caption("Beautiful sunset at the beach")
profile_tags = ig.ai_suggest.hashtags_for_profile("cristiano")
captions = ig.ai_suggest.caption_ideas("travel", style="casual", count=5)
```

### 👥 Audience Finder

```python
lookalike = ig.audience.find_lookalike("competitor", count=50)
overlap = ig.audience.overlap("account_a", "account_b")
insights = ig.audience.insights("my_account")
```

### 💬 Comment Manager

```python
comments = ig.comment_manager.get_comments(media_pk, sort="top")
ig.comment_manager.auto_reply(media_pk, keyword="price?", reply="DM us!")
ig.comment_manager.delete_spam(media_pk)
sentiment = ig.comment_manager.sentiment(media_pk)
```

### 🧪 A/B Testing

```python
test = ig.ab_test.create("Caption Test", variants={
    "A": {"caption": "Short and sweet"},
    "B": {"caption": "Long detailed caption with hashtags #test"},
})
ig.ab_test.record(test["id"], "A", likes=100, comments=20)
ig.ab_test.record(test["id"], "B", likes=150, comments=30)
result = ig.ab_test.results(test["id"])
print(f"Winner: {result['winner']}")
```

---

## Pydantic Models

All API methods return typed Pydantic models with dict-like access:

```python
user = ig.users.get_by_username("cristiano")

# Typed attributes
print(user.username)          # "cristiano"
print(user.followers)         # 650000000

# Dict-like access (backward compatible)
print(user["username"])       # "cristiano"

# Convert to dict
data = user.to_dict()

# Extra fields preserved (API changes won't break)
print(user.get("some_new_field"))    # returns field if present in payload
```

**Available models:** `InstaModel`, `User`, `UserShort`, `Contact`, `BioParsed`, `Media`, `Caption`, `Comment`, `Story`, `StorySticker`, `Highlight`, `DirectThread`, `DirectMessage`, `Location`, `ImageVersion`, `Pagination`, `HashtagSearchResult`, `Notification`, `NotifInbox`, `PublicProfile`, `PublicPost`, `HashtagPost`, `ProfileSnapshot`, `PublicDataReport`

---

## Features

| Feature | Description |
| --------- | ------------- |
| 🛡️ **Anti-detection** | Coherent Chrome TLS/header profiles (`chrome142`/`chrome136`), session-locked fingerprints, Gaussian delays, escalation |
| 🔄 **Multi-account** | Automatic session rotation & cooldowns |
| 🌐 **Proxy support** | SOCKS5/HTTP, weighted rotation, health checking |
| ⏱️ **Rate limiting** | Per-endpoint sliding window limits + `TokenBucketLimiter` in `core/` |
| 🔐 **Login** | NaCl encrypted password, 2FA, checkpoint handling |
| 💾 **Session persistence** | Save/load sessions, no re-login needed |
| 🧩 **Challenge handler** | Auto-resolve email/SMS/consent challenges |
| ⚡ **Full async parity** | 33 sync + 34 async lazy modules (33 async API mirrors + `batch`) |
| 📦 **Pydantic models** | Typed returns, dict-like access, backward compatible |
| 🤖 **AI Agent** | 11 AI providers, 162 tools, natural language control, memory, webhooks |
| 📊 **Advanced tools** | Analytics, Export, Growth, Automation, Monitor, Pipeline, Diagnostics |
| 🔬 **Diagnostics** | 41-method health check (sync+async), CLI support, JSON output |
| 🏗️ **Core infra** | Circuit breaker, token bucket, response cache, connection pool, metrics, structured logging |
| ✅ **CI/CD** | GitHub Actions — lint, test (4 Python versions), security, build |
| 🧪 **6292 tests** | pytest, unit, contract, and AST invariant tests |

## Core Infrastructure

`instaharvest_v2.core` provides runtime resilience primitives with zero external runtime dependencies:

| Component | Purpose |
| --------- | ------- |
| **CircuitBreaker** | Per-endpoint three-state failure isolation (`CLOSED` → `OPEN` → `HALF_OPEN`) used by `HttpClient` and `AsyncHttpClient`. |
| **TokenBucketLimiter** | O(1) sync + async token bucket rate limiter with burst capacity alongside `HttpClient`'s sliding-window `RateLimiter`. |
| **ResponseCache** | LRU + TTL cache used by `AnonClient` (`PublicAPI.get_profile`, `PublicAPI.get_post_by_shortcode`) with stale-while-revalidate support. |
| **ConnectionPool** | `curl_cffi` session pool helper with health tracking. |
| **Metrics** | Prometheus-compatible counters, gauges, and histograms (`metrics` registry). |
| **StructuredLogger** | JSON log entries with correlation IDs and PII redaction. |

### Lazy-Loading Architecture

`Instagram` (33 modules) and `AsyncInstagram` (34 modules, including `batch`) load API modules on first attribute access via `__getattr__` and `_lazy_modules.py` (`resolve_lazy_module`), avoiding upfront initialization of unused modules.

### Metrics & Observability

```python
from instaharvest_v2.core import metrics
print(metrics.snapshot())
print(metrics.export_prometheus())
```

HTTP requests emit duration, error, retry, and short-circuit metrics declared in `_http_metrics.py`.

### Response Cache (Anonymous API)

```python
ig = Instagram.anonymous()
profile = ig.public.get_profile("cristiano")  # fetches and caches (5min TTL)
profile = ig.public.get_profile("cristiano")  # cache hit

stats = ig.public.cache_stats  # {size, hits, misses, hit_rate}
ig.public.invalidate_cache(prefix="get_profile:")  # force refresh
```

`get_profile()` and `get_post_by_shortcode()` on `PublicAPI` use `cached_call()` with a 5-minute default TTL and stale-while-revalidate.

---

## Speed Modes (Async)

```python
# 🐢 SAFE  — 5 concurrent, human delays
async with AsyncInstagram.from_env(mode="safe") as ig: ...

# ⚡ FAST  — 15 concurrent, moderate delays
async with AsyncInstagram.from_env(mode="fast") as ig: ...

# 🚀 TURBO — 50 concurrent, minimal delays (proxy required)
async with AsyncInstagram.from_env(mode="turbo") as ig: ...
```

---

## Testing & Quality

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=instaharvest_v2 --cov-report=term-missing
```

**Current status:**

- ✅ 6292 tests passed (41 skipped)
- 📊 ~83.6% CI coverage baseline (core package; `agent/` and `web/` excluded; >70% fail-under gate)

---

## Project Structure

```text
instaharvest_v2/
├── instagram.py           # Main class (sync, lazy-loading)
├── async_instagram.py     # Main class (async, lazy-loading)
├── client.py              # HTTP client (curl_cffi + HttpClient.request)
├── async_client.py        # Async HTTP client (+ AsyncHttpClient.request)
├── anon_client.py         # Anonymous scraping client (sync)
├── async_anon_client.py   # Anonymous scraping client (async)
├── http_utils.py          # Shared URL normalization, headers, maybe_await()
├── diagnostics.py         # API diagnostics (41 methods, sync+async)
├── parsers.py             # Shared parser functions (20 functions)
├── challenge.py           # Challenge auto-resolver
├── anti_detect.py         # Anti-detection system
├── smart_rotation.py      # Multi-signal rotation coordinator
├── session_manager.py     # Session auto-refresh
├── proxy_manager.py       # Proxy rotation
├── rate_limiter.py        # Rate limiting
├── multi_account.py       # Multi-account manager
├── exceptions.py          # Error classes
├── _lazy_modules.py       # Lazy API module registry (sync + async)
├── _endpoint_keys.py      # URL normalization for circuit breakers/metrics
├── _http_metrics.py       # Pre-declared HTTP metric instances
├── models/                # Pydantic models
│   ├── base.py            # InstaModel base class
│   ├── common.py          # ImageVersion, Pagination
│   ├── user.py            # User, UserShort, Contact, BioParsed
│   ├── media.py           # Media, Caption
│   ├── comment.py         # Comment
│   ├── story.py           # Story, Highlight, StorySticker
│   ├── direct.py          # DirectThread, DirectMessage
│   ├── location.py        # Location
│   ├── hashtag.py         # HashtagSearchResult
│   ├── notification.py    # Notification, NotifInbox
│   └── public_data.py     # PublicProfile, PublicPost, HashtagPost, etc.
├── core/                  # Infrastructure layer
│   ├── circuit_breaker.py # Three-state failure isolation
│   ├── token_bucket.py    # O(1) rate limiting with burst
│   ├── response_cache.py  # LRU + TTL cache
│   ├── connection_pool.py # curl_cffi session pooling
│   ├── metrics.py         # Prometheus-compatible metrics
│   └── structured_logging.py # JSON logs with correlation IDs
├── api/                   # API modules (31 sync + 2 subpkgs = 33 lazy; 33 async mirrors)
│   ├── users.py           # User profiles
│   ├── media.py           # Post interactions
│   ├── feed.py            # User feeds
│   ├── friendships.py     # Follow/unfollow
│   ├── search.py          # Search
│   ├── stories.py         # Stories & highlights
│   ├── direct.py          # Direct messages
│   ├── upload.py          # Photo/video upload
│   ├── download.py        # Media downloads
│   ├── hashtags.py        # Hashtag info & sections
│   ├── insights.py        # Account & media insights
│   ├── location.py        # Location feeds & info
│   ├── collections.py     # Saved collections
│   ├── notifications.py   # Activity & inbox notifications
│   ├── public.py          # Anonymous public API
│   ├── auth/              # Login, session, encryption (5 modules)
│   ├── graphql/           # GraphQL v2 (doc_id transport, 7 modules)
│   ├── analytics.py       # Engagement analytics
│   ├── export.py          # CSV/JSON export
│   ├── growth.py          # Smart follow/unfollow
│   ├── automation.py      # Bot framework
│   ├── scheduler.py       # Post scheduling
│   ├── monitor.py         # Account monitoring
│   ├── bulk_download.py   # Bulk media download
│   ├── hashtag_research.py # Hashtag analysis
│   ├── pipeline.py        # Data pipeline (SQLite/JSONL)
│   ├── ai_suggest.py      # AI hashtag/caption
│   ├── audience.py        # Lookalike audience
│   ├── comment_manager.py # Comment management
│   ├── ab_test.py         # A/B testing
│   ├── public_data.py     # Public data analytics
│   ├── discover.py        # Similar user discovery
│   └── async_*.py         # 33 async_*.py mirrors (+ batch.py on AsyncInstagram)
├── agent/                 # AI Agent system
│   ├── core.py            # InstaAgent main class
│   ├── providers/         # 11 AI providers across 4 adapter modules
│   ├── tools/             # 162 built-in tools across 13 modules
│   │   ├── instagram_tools.py  # Instagram tools (profile, posts, reels, comments)
│   │   ├── media_tools.py      # Media & social tools (download, follow, like)
│   │   ├── file_tools.py       # File I/O tools
│   │   ├── system_tools.py     # File management, sessions, system info
│   │   ├── analysis_tools.py   # Data analysis & charts
│   │   ├── network_tools.py    # HTTP, search, DM
│   │   ├── auth_tools.py       # Login, validate, logout
│   │   ├── analytics_tools.py  # Analytics, insights, audience, A/B test
│   │   ├── automation_tools.py # Automation, scheduler, monitor
│   │   ├── export_tools.py     # CSV/JSON export tools
│   │   ├── growth_tools.py     # Growth follow/unfollow tools
│   │   ├── pipeline_tools.py   # Pipeline, bulk download, AI suggest
│   │   └── utility_tools.py    # JSON, CSV, calculate, merge, download
│   ├── memory.py          # Conversation memory
│   ├── templates.py       # 10 task templates
│   ├── tui.py             # Terminal UI (Rich)
│   ├── web.py             # Web UI (FastAPI)
│   ├── webhook.py         # Notifications (Telegram, Discord)
│   ├── cost_tracker.py    # Token usage & pricing
│   └── vision.py          # Multimodal image analysis
tests/                     # 6292 tests
docs/                      # MkDocs documentation
.github/workflows/         # CI/CD pipeline
```

## CI/CD

GitHub Actions pipelines (`.github/workflows/ci.yml` and `.github/workflows/docs.yml`):

| Workflow / Job | Description |
| -------------- | ----------- |
| **Lint** | flake8 + mypy (`ci.yml`) |
| **Test** | Python 3.10, 3.11, 3.12, 3.13 + coverage (`ci.yml`) |
| **Security** | bandit + safety (`ci.yml`) |
| **Build** | Package + twine check (`ci.yml`) |
| **Docs** | MkDocs Material build & deploy to `gh-pages` (`docs.yml`) |

## ⚠️ Legal Disclaimer

This library is an unofficial, third-party tool designed for educational and research purposes only. It is not affiliated with, authorized, maintained, sponsored, or endorsed by Instagram or Meta Platforms, Inc.

By using this software, you agree that:

1. You are **solely responsible** for any actions you take using this library.
2. The authors and maintainers are **NOT** responsible or liable for any bans, blocks, suspensions, or other penalties applied to your Instagram accounts or IP addresses.
3. You will use this tool in compliance with Instagram's Terms of Service and all applicable local laws.

Use at your own risk. The software is provided "AS IS", without warranty of any kind.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
