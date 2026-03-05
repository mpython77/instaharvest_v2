<p align="center">
  <h1 align="center">📸 InstaHarvest v2</h1>
  <p align="center">
    <strong>Powerful Instagram Private API</strong> — async, anti-detection, Pydantic models, AI Agent
  </p>
  <p align="center">
    <a href="https://pypi.org/project/instaharvest-v2/"><img src="https://img.shields.io/pypi/v/instaharvest-v2?color=blue" alt="PyPI"></a>
    <a href="https://pypi.org/project/instaharvest-v2/"><img src="https://img.shields.io/pypi/pyversions/instaharvest-v2" alt="Python"></a>
    <a href="https://github.com/mpython77/instaharvest_v2/blob/main/LICENSE"><img src="https://img.shields.io/github/license/mpython77/instaharvest_v2" alt="License"></a>
    <img src="https://img.shields.io/badge/modules-32+32-green" alt="Modules">
    <img src="https://img.shields.io/badge/async-full_parity-brightgreen" alt="Async">
    <img src="https://img.shields.io/badge/tests-489_passed-success" alt="Tests">
    <img src="https://img.shields.io/badge/coverage-35%25-green" alt="Coverage">
    <a href="https://mpython77.github.io/instaharvest_v2/"><img src="https://img.shields.io/badge/docs-online-blue?logo=readthedocs" alt="Docs"></a>
  </p>
</p>

> 32 sync + 32 async modules • 230+ functions • Pydantic models • AI Agent • CI/CD • 489 tests passed
>
> 📖 **Documentation:** [mpython77.github.io/instaharvest_v2](https://mpython77.github.io/instaharvest_v2/)

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
print(user["bio"])           # dict-like access works too
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

### Async mode (50x faster for bulk)

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
ig = Instagram.anonymous()
profile = ig.public.get_profile("cristiano")
posts = ig.public.get_posts("cristiano", max_count=12)
```

### 🎬 Reel / Post Scraping (no login, no cookies!)

```python
ig = Instagram()

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

### 🤖 AI Agent

```python
from instaharvest_v2 import Instagram
from instaharvest_v2.agent import InstaAgent, Permission

ig = Instagram.from_env(".env")
agent = InstaAgent(
    ig=ig,
    provider="gemini",        # 13 AI providers
    permission=Permission.FULL_ACCESS,
    memory=True,
)

agent.ask("Get @cristiano's last 10 posts and save to CSV")
agent.ask("Compare @nike and @adidas engagement rates")
agent.ask("Find the best posting time for my account")
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

### 📰 Feed

```python
ig.feed.get_user_feed(user_pk)
posts = ig.feed.get_all_posts(user_pk, max_posts=100)
ig.feed.get_liked()
ig.feed.get_saved()
ig.feed.get_tag_feed("fashion")
ig.feed.get_location_feed(location_pk)
ig.feed.get_timeline()
ig.feed.get_reels_feed()
```

### 📖 Stories

```python
ig.stories.get_tray()
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
ig.direct.send_media(thread_id, media_pk)
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

### More Core Modules

```python
ig.hashtags.get_info("fashion")        # Hashtag info
ig.insights.get_account_insights()     # Analytics
ig.notifications.get_activity_feed()   # Notifications
ig.graphql.get_followers(user_pk)      # GraphQL queries
ig.location.search("New York")         # Location search
ig.collections.get_list()              # Saved collections
```

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
print(user.follower_count)    # 650000000

# Dict-like access (backward compatible)
print(user["username"])       # "cristiano"

# Convert to dict
data = user.to_dict()

# Extra fields preserved (API changes won't break)
print(user.some_new_field)    # works!
```

**Available models:** `User`, `UserShort`, `Media`, `Comment`, `Story`, `Highlight`, `DirectThread`, `DirectMessage`, `Location`, `Hashtag`, `Notification`

---

## Features

| Feature | Description |
|---------|-------------|
| 🛡️ **Anti-detection** | Browser fingerprint rotation, Gaussian delays, escalation |
| 🔄 **Multi-account** | Automatic session rotation |
| 🌐 **Proxy support** | SOCKS5/HTTP, weighted rotation, health checking |
| ⏱️ **Rate limiting** | Per-endpoint sliding window limits |
| 🔐 **Login** | NaCl encrypted password, 2FA, checkpoint handling |
| 💾 **Session persistence** | Save/load sessions, no re-login needed |
| 🧩 **Challenge handler** | Auto-resolve email/SMS/consent challenges |
| ⚡ **Full async parity** | 32 sync + 32 async modules — complete feature match |
| 📦 **Pydantic models** | Typed returns, dict-like access, backward compatible |
| 🤖 **AI Agent** | 13 providers, natural language control, memory, webhooks |
| 📊 **12 Advanced tools** | Analytics, Export, Growth, Automation, Monitor, Pipeline, etc. |
| ✅ **CI/CD** | GitHub Actions — lint, test (3 Python versions), security, build |
| 🧪 **489 tests** | 35% coverage, pytest-cov, comprehensive unit & integration tests |

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

- ✅ 489 tests passed
- 📊 35.3% code coverage

---

## Project Structure

```
instaharvest_v2/
├── instagram.py           # Main class (sync)
├── async_instagram.py     # Main class (async)
├── client.py              # HTTP client (curl_cffi)
├── async_client.py        # Async HTTP client
├── anon_client.py         # Anonymous scraping client (sync)
├── async_anon_client.py   # Anonymous scraping client (async)
├── parsers.py             # Shared parser functions (8 standalone)
├── challenge.py           # Challenge auto-resolver
├── anti_detect.py         # Anti-detection system
├── smart_rotation.py      # Multi-signal rotation coordinator
├── session_manager.py     # Session auto-refresh
├── proxy_manager.py       # Proxy rotation
├── rate_limiter.py        # Rate limiting
├── multi_account.py       # Multi-account manager
├── exceptions.py          # Error classes
├── models/                # Pydantic models
│   ├── user.py            # User, UserShort, BioParsed
│   ├── media.py           # Media, Caption
│   ├── comment.py         # Comment
│   ├── story.py           # Story, Highlight
│   ├── direct.py          # DirectThread, DirectMessage
│   ├── location.py        # Location
│   ├── notification.py    # Notification models
│   └── public_data.py     # PublicProfile, PublicPost
├── api/                   # API modules (33 sync + 33 async)
│   ├── users.py           # User profiles
│   ├── media.py           # Post interactions
│   ├── feed.py            # User feeds
│   ├── friendships.py     # Follow/unfollow
│   ├── search.py          # Search
│   ├── stories.py         # Stories & highlights
│   ├── direct.py          # Direct messages
│   ├── upload.py          # Photo/video upload
│   ├── download.py        # Media downloads
│   ├── auth.py            # Login/logout
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
│   └── async_*.py         # All 33 async mirrors
├── agent/                 # AI Agent system
│   ├── core.py            # InstaAgent main class
│   ├── providers/         # AI providers (Gemini, OpenAI, Claude, etc.)
│   ├── tools.py           # 10 built-in tools
│   ├── memory.py          # Conversation memory
│   ├── templates.py       # 10 task templates
│   ├── tui.py             # Terminal UI (Rich)
│   ├── web.py             # Web UI (FastAPI)
│   ├── webhook.py         # Notifications (Telegram, Discord)
│   ├── cost_tracker.py    # Token usage & pricing
│   └── vision.py          # Multimodal image analysis
tests/                     # 489 tests
docs/                      # MkDocs documentation
.github/workflows/         # CI/CD pipeline
```

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

| Job | Description |
|-----|-------------|
| **Lint** | flake8 + mypy |
| **Test** | Python 3.10, 3.11, 3.12 + coverage |
| **Security** | bandit + safety |
| **Build** | Package + twine check |

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
