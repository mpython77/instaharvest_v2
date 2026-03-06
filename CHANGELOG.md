# Changelog

## [1.0.23] — 2026-03-06

### Removed

- **browser_engine.py** — Completely removed Playwright-based BrowserEngine from the library
- **async_client.py** — Removed BrowserEngine import, lazy initialization, POST routing, and close() cleanup
- POST requests now go directly through `curl_cffi` (as originally designed)

### Changed

- **async_direct.py** — `create_thread()` now generates proper Web API payload with `client_context`, `mutation_token`, `offline_threading_id`, `_uuid` (UUID v4), and `action: send_item`
- **async_direct.py** — `recipient_users` format fixed to nested array `[["user_id"]]` matching Instagram Web API spec

### Notes

- Playwright integration was attempted to bypass Instagram's WAF on POST requests (302 redirect filter), but Instagram's Datadome anti-bot system detects and blocks even real Chromium instances when cookies are injected programmatically
- The library's core strength remains in GET-based scraping via `curl_cffi` with TLS impersonation

---

## [1.0.22] — 2026-03-06

### Fixed

- **async_discover.py** — Updated old doc_id (`29042405687261020`) to verified (`25814188068245954`)
- **async_discover.py** — Fixed `module` variable and `friendly_name` to match sync version
- **async_discover.py** — Added async `chain()` method with memory guard (`max_total`)
- **async_graphql.py** — Added 7 missing methods: `get_hover_card`, `get_suggested_users`, `like_media`, `get_timeline_v2`, `get_reels_trending_v2`, `get_saved_v2`, `_parse_timeline_connection`
- **async_graphql.py** — Fixed `get_comments_v2` variables to match verified format
- **async_feed.py** — Added GraphQL v2 + REST fallback for `get_timeline`, `get_all_timeline`, `get_reels_feed`
- **discover.py** — Added `max_total=10000` memory guard to `chain()`
- **discover.py**, **users.py**, **README.md** — Translated all comments to English

### Added

- `CHANGELOG.md` — Version history tracking

---

## [1.0.21] — 2026-03-06

### Added

- **graphql.py** — 16 verified doc_ids from browser inspection
- **graphql.py** — New methods: `get_hover_card`, `get_suggested_users`, `like_media`, `get_comments_v2`, `get_timeline_v2`, `get_reels_trending_v2`, `get_saved_v2`
- **discover.py** — `chain()` method for multi-layer lead discovery
- **feed.py** — GraphQL v2 + REST fallback architecture
- **test_graphql_v2.py** — 18 unit tests for all new methods

### Changed

- Marked 6 unverified doc_ids with `UNVERIFIED` comment

---

## [1.0.20] — 2026-03-05

### Added

- `full_scrape.py` v3.1 — Suggested users integration
- `README.md` — GraphQL API v2 documentation section
