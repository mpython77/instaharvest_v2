# Changelog

## [1.1.29] — 2026-04-12

### Added (v1.1.29)

- **agent/tools/utility_tools.py** — 7 new utility tools:
  - `json_parse`, `csv_to_json`, `json_to_csv`, `calculate`, `text_replace`, `merge_files`, `download_url`
- **agent/tools/** — Phase 5 tools (47 new tools across auth, analytics, export, automation, pipeline):
  - Auth tools (3): `login`, `validate_session`, `logout`
  - Analytics tools (8): `engagement_rate`, `best_posting_times`, `compare_accounts`, etc.
  - Export tools (6): `export_followers_csv`, `export_to_json`, `save_to_sqlite`, etc.
  - Automation tools (17): `auto_dm_new_followers`, `schedule_post`, `monitor_account`, etc.
  - Pipeline tools (12): `pipeline_to_sqlite`, `bulk_download_posts`, `ai_suggest_hashtags`, etc.
- Agent TOOL_HANDLERS expanded from 37 → **161 tools** (164 schemas)
- 6242 tests passing (up from 489)

### Fixed (v1.1.29)

- **agent/core.py** — Critical dispatch bug: generic `_execute_tool` fallback was not passing `ig=`, `is_logged_in=`, `cache=` arguments to Phase 5 tool handlers, causing all new tools to fail at runtime
- **README.md** — Updated all outdated statistics (modules, tools, tests, coverage, project structure)

### Removed (v1.1.4)

- Cleaned up 49 unused `cov*.txt` coverage dump files
- Cleaned up 11 unused `.json` test artifacts
- Removed `debug_logs/`, `htmlcov/`, `.pytest_cache/`, `dist/`, `downloads/`, `smart_proxy/` directories
- Removed `test_live_agent.py`, `test_pro_arch.py`, `test_agent_tools.py`, `measure_coverage.py` (contained hardcoded API keys)
- Added `my_test/` to `.gitignore`

---

## [1.0.24] — 2026-03-16

### Added (v1.0.24)

- **diagnostics.py** — Full API diagnostics module (41 methods: 22 PublicAPI + 19 AnonClient low-level)
  - Sync + async testing, registry pattern, JSON output, CLI integration
  - `run_diagnostics()`, `get_registered_methods()`, `MethodResult` exported from package
- **cli.py** — `diagnose` subcommand: `python -m instaharvest_v2 diagnose cristiano --proxy ...`
- **agent/tools/instagram_tools.py** — 15 new anonymous tool handlers:
  - `get_user_id`, `is_public`, `exists`, `get_feed`, `get_all_posts`, `get_reels`,
    `get_comments`, `get_highlights`, `get_similar_accounts`, `get_post_by_shortcode`,
    `get_post_by_url`, `get_media_urls`, `get_hashtag_posts`, `get_location_posts`,
    `run_diagnostics`
- Agent TOOL_HANDLERS expanded from 23 → 37 tools

### Changed (v1.0.24)

- **agent/tools/instagram_tools.py** — `get_hashtag_info` no longer requires login (uses `ig.public.get_hashtag_posts_v2` with login fallback)
- **README.md** — Updated module counts (33+33), added Public Anonymous API section (22 methods), Diagnostics section, project structure

### Removed (v1.0.24)

- **my_test/anon_api.py** — Migrated to `instaharvest_v2/diagnostics.py`
- **my_test/_check_coverage.py** — No longer needed

---

## [1.0.23] — 2026-03-06

### Removed (v1.0.23)

- **browser_engine.py** — Completely removed Playwright-based BrowserEngine from the library
- **async_client.py** — Removed BrowserEngine import, lazy initialization, POST routing, and close() cleanup
- POST requests now go directly through `curl_cffi` (as originally designed)

### Changed (v1.0.23)

- **async_direct.py** — `create_thread()` now generates proper Web API payload with `client_context`, `mutation_token`, `offline_threading_id`, `_uuid` (UUID v4), and `action: send_item`
- **async_direct.py** — `recipient_users` format fixed to nested array `[["user_id"]]` matching Instagram Web API spec

### Notes

- Playwright integration was attempted to bypass Instagram's WAF on POST requests (302 redirect filter), but Instagram's Datadome anti-bot system detects and blocks even real Chromium instances when cookies are injected programmatically
- The library's core strength remains in GET-based scraping via `curl_cffi` with TLS impersonation

---

## [1.0.22] — 2026-03-06

### Fixed (v1.0.22)

- **async_discover.py** — Updated old doc_id (`29042405687261020`) to verified (`25814188068245954`)
- **async_discover.py** — Fixed `module` variable and `friendly_name` to match sync version
- **async_discover.py** — Added async `chain()` method with memory guard (`max_total`)
- **async_graphql.py** — Added 7 missing methods: `get_hover_card`, `get_suggested_users`, `like_media`, `get_timeline_v2`, `get_reels_trending_v2`, `get_saved_v2`, `_parse_timeline_connection`
- **async_graphql.py** — Fixed `get_comments_v2` variables to match verified format
- **async_feed.py** — Added GraphQL v2 + REST fallback for `get_timeline`, `get_all_timeline`, `get_reels_feed`
- **discover.py** — Added `max_total=10000` memory guard to `chain()`
- **discover.py**, **users.py**, **README.md** — Translated all comments to English

### Added (v1.0.22)

- `CHANGELOG.md` — Version history tracking

---

## [1.0.21] — 2026-03-06

### Added (v1.0.21)

- **graphql.py** — 16 verified doc_ids from browser inspection
- **graphql.py** — New methods: `get_hover_card`, `get_suggested_users`, `like_media`, `get_comments_v2`, `get_timeline_v2`, `get_reels_trending_v2`, `get_saved_v2`
- **discover.py** — `chain()` method for multi-layer lead discovery
- **feed.py** — GraphQL v2 + REST fallback architecture
- **test_graphql_v2.py** — 18 unit tests for all new methods

### Changed (v1.0.21)

- Marked 6 unverified doc_ids with `UNVERIFIED` comment

---

## [1.0.20] — 2026-03-05

### Added (v1.0.20)

- `full_scrape.py` v3.1 — Suggested users integration
- `README.md` — GraphQL API v2 documentation section
