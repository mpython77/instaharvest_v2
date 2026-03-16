"""
InstaHarvest v2 Diagnostics — Public Anonymous API Health Check
================================================================
Tests all public anonymous API methods (sync + async) across
two layers: PublicAPI (high-level) and AnonClient (low-level).

Usage as library:
    from instaharvest_v2 import Instagram
    from instaharvest_v2.diagnostics import run_diagnostics

    ig = Instagram.anonymous(unlimited=True)
    ig.add_proxy("http://proxy...")
    results = run_diagnostics(ig, username="cristiano")

Usage from CLI:
    python -m instaharvest_v2 diagnose cristiano
    python -m instaharvest_v2 diagnose cristiano --proxy http://...
    python -m instaharvest_v2 diagnose cristiano --layer public --sync-only
"""

import json
import time
import asyncio
import inspect
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════

@dataclass
class MethodResult:
    """Single API method result."""
    name: str = ""
    mode: str = ""          # "sync" / "async"
    layer: str = ""         # "public" / "low-level"
    status: str = "skip"    # "ok" / "error" / "none" / "skip"
    elapsed: float = 0.0
    data_type: str = ""
    data_keys: List[str] = field(default_factory=list)
    data_count: int = 0
    data_sample: Any = None
    error: str = ""
    raw_data: Any = None


# ═══════════════════════════════════════════════════════════
# METHOD REGISTRY
# ═══════════════════════════════════════════════════════════

REGISTRY: List[dict] = []


def _register(name: str, layer: str = "public", category: str = "profile",
              needs_user_id=False, needs_shortcode=False, needs_media_id=False):
    """Decorator — register diagnostic methods."""
    def decorator(fn_builder):
        REGISTRY.append({
            "name": name,
            "layer": layer,
            "category": category,
            "needs_user_id": needs_user_id,
            "needs_shortcode": needs_shortcode,
            "needs_media_id": needs_media_id,
            "fn_builder": fn_builder,
        })
        return fn_builder
    return decorator


# ═══════════════════════════════════════════════════════════
# LAYER 1: PUBLIC API (high-level, ig.public.*)
# ═══════════════════════════════════════════════════════════

# ── PROFILE ──
@_register("get_profile", layer="public", category="profile")
def _b(api, ctx): return lambda: api.get_profile(ctx["username"])

@_register("get_user_id", layer="public", category="profile")
def _b(api, ctx): return lambda: api.get_user_id(ctx["username"])

@_register("get_profile_pic_url", layer="public", category="profile")
def _b(api, ctx): return lambda: api.get_profile_pic_url(ctx["username"])

@_register("is_public", layer="public", category="profile")
def _b(api, ctx): return lambda: api.is_public(ctx["username"])

@_register("exists", layer="public", category="profile")
def _b(api, ctx): return lambda: api.exists(ctx["username"])

# ── DISCOVERY ──
@_register("search", layer="public", category="discovery")
def _b(api, ctx): return lambda: api.search(ctx["username"])

@_register("get_similar_accounts", layer="public", category="discovery")
def _b(api, ctx): return lambda: api.get_similar_accounts(ctx["username"])

# ── CONTENT ──
@_register("get_posts", layer="public", category="content")
def _b(api, ctx): return lambda: api.get_posts(ctx["username"], max_count=6)

@_register("get_feed", layer="public", category="content", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_feed(ctx["user_id"], max_count=6)

@_register("get_all_posts", layer="public", category="content")
def _b(api, ctx): return lambda: api.get_all_posts(ctx["username"], max_count=6)

@_register("get_post_by_shortcode", layer="public", category="content", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_post_by_shortcode(ctx["shortcode"])

@_register("get_post_by_url", layer="public", category="content", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_post_by_url(f"https://www.instagram.com/p/{ctx['shortcode']}/")

@_register("get_media", layer="public", category="content", needs_media_id=True)
def _b(api, ctx): return lambda: api.get_media(ctx["media_id"])

@_register("get_media_urls", layer="public", category="content", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_media_urls(ctx["shortcode"])

@_register("get_reels", layer="public", category="content")
def _b(api, ctx): return lambda: api.get_reels(ctx["username"], max_count=3)

@_register("get_comments", layer="public", category="content", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_comments(ctx["shortcode"], max_count=5)

@_register("get_highlights", layer="public", category="content")
def _b(api, ctx): return lambda: api.get_highlights(ctx["username"])

# ── HASHTAG ──
@_register("get_hashtag_posts", layer="public", category="hashtag")
def _b(api, ctx): return lambda: api.get_hashtag_posts(ctx["hashtag"], max_count=3)

@_register("get_hashtag_posts_v2", layer="public", category="hashtag")
def _b(api, ctx): return lambda: api.get_hashtag_posts_v2(ctx["hashtag"], max_count=3)

# ── LOCATION ──
@_register("get_location_posts", layer="public", category="location")
def _b(api, ctx): return lambda: api.get_location_posts(ctx["location_id"], max_count=3)

# ── BULK ──
@_register("bulk_profiles", layer="public", category="bulk")
def _b(api, ctx): return lambda: api.bulk_profiles([ctx["username"]], workers=1)

@_register("bulk_feeds", layer="public", category="bulk", needs_user_id=True)
def _b(api, ctx): return lambda: api.bulk_feeds([ctx["user_id"]], max_count=3, workers=1)


# ═══════════════════════════════════════════════════════════
# LAYER 2: LOW-LEVEL ANON CLIENT (direct client.* access)
# ═══════════════════════════════════════════════════════════

# ── HTML / Web parse ──
@_register("ll_get_profile_html", layer="low-level", category="html-parse")
def _b(api, ctx): return lambda: api.get_profile_html(ctx["username"])

@_register("ll_get_web_profile", layer="low-level", category="web-api")
def _b(api, ctx): return lambda: api.get_web_profile(ctx["username"])

@_register("ll_get_profile_chain", layer="low-level", category="chain")
def _b(api, ctx): return lambda: api.get_profile_chain(ctx["username"])

# ── Post strategies ──
@_register("ll_get_embed_data", layer="low-level", category="post-strategy", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_embed_data(ctx["shortcode"])

@_register("ll_get_post_chain", layer="low-level", category="chain", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_post_chain(ctx["shortcode"])

# ── GraphQL ──
@_register("ll_get_user_posts_graphql", layer="low-level", category="graphql", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_user_posts_graphql(str(ctx["user_id"]), first=6)

@_register("ll_get_post_comments_graphql", layer="low-level", category="graphql", needs_shortcode=True)
def _b(api, ctx): return lambda: api.get_post_comments_graphql(ctx["shortcode"], first=5)

@_register("ll_get_hashtag_posts_graphql", layer="low-level", category="graphql")
def _b(api, ctx): return lambda: api.get_hashtag_posts_graphql(ctx["hashtag"], first=3)

# ── Mobile API ──
@_register("ll_get_user_info_mobile", layer="low-level", category="mobile-api", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_user_info_mobile(ctx["user_id"])

@_register("ll_get_media_info_mobile", layer="low-level", category="mobile-api", needs_media_id=True)
def _b(api, ctx): return lambda: api.get_media_info_mobile(ctx["media_id"])

@_register("ll_get_user_feed_mobile", layer="low-level", category="mobile-api", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_user_feed_mobile(str(ctx["user_id"]), count=6)

@_register("ll_get_user_reels", layer="low-level", category="mobile-api", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_user_reels(ctx["user_id"], count=3)

@_register("ll_get_similar_accounts", layer="low-level", category="mobile-api", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_similar_accounts(ctx["user_id"])

@_register("ll_get_highlights_tray", layer="low-level", category="mobile-api", needs_user_id=True)
def _b(api, ctx): return lambda: api.get_highlights_tray(ctx["user_id"])

# ── Web API endpoints ──
@_register("ll_search_web", layer="low-level", category="web-api")
def _b(api, ctx): return lambda: api.search_web(ctx["username"])

@_register("ll_get_hashtag_sections", layer="low-level", category="web-api")
def _b(api, ctx): return lambda: api.get_hashtag_sections(ctx["hashtag"])

@_register("ll_get_location_sections", layer="low-level", category="web-api")
def _b(api, ctx): return lambda: api.get_location_sections(ctx["location_id"])

# ── Stats ──
@_register("ll_request_count", layer="low-level", category="stats")
def _b(api, ctx): return lambda: api.request_count

@_register("ll_error_count", layer="low-level", category="stats")
def _b(api, ctx): return lambda: api.error_count


# ═══════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════

def _summarize(data: Any) -> dict:
    """Summarize data — type, keys, count, sample."""
    if data is None:
        return {"data_type": "None", "data_keys": [], "data_count": 0, "data_sample": None}
    if isinstance(data, dict):
        keys = list(data.keys())
        sample = {}
        for k in keys[:12]:
            v = data[k]
            if isinstance(v, (str, int, float, bool, type(None))):
                sample[k] = v if not isinstance(v, str) or len(v) <= 100 else v[:100]
            elif isinstance(v, list):
                sample[k] = f"list[{len(v)}]"
                if v and isinstance(v[0], dict):
                    sample[k] += f" keys: {sorted(v[0].keys())[:6]}"
            elif isinstance(v, dict):
                sample[k] = f"dict[{len(v)} keys]"
            else:
                sample[k] = str(type(v).__name__)
        return {"data_type": "dict", "data_keys": keys, "data_count": len(keys), "data_sample": sample}
    if isinstance(data, list):
        sample = []
        for item in data[:3]:
            if isinstance(item, dict):
                sample.append({k: (v if not isinstance(v, str) or len(v) <= 80 else v[:80])
                               for k, v in list(item.items())[:8]})
            else:
                sample.append(item)
        return {"data_type": "list", "data_keys": [], "data_count": len(data), "data_sample": sample}
    if isinstance(data, (str, bool, int, float)):
        return {"data_type": type(data).__name__, "data_keys": [], "data_count": 1,
                "data_sample": data if not isinstance(data, str) or len(data) <= 200 else data[:200]}
    return {"data_type": str(type(data).__name__), "data_keys": [], "data_count": 1, "data_sample": str(data)[:200]}


def _run_method(name: str, mode: str, layer: str, fn: Callable) -> MethodResult:
    """Execute sync method."""
    r = MethodResult(name=name, mode=mode, layer=layer)
    t0 = time.time()
    try:
        data = fn()
        r.elapsed = round(time.time() - t0, 2)
        r.status = "none" if data is None else "ok"
        s = _summarize(data)
        r.data_type, r.data_keys, r.data_count, r.data_sample = s["data_type"], s["data_keys"], s["data_count"], s["data_sample"]
        r.raw_data = data
    except Exception as e:
        r.elapsed = round(time.time() - t0, 2)
        r.status = "error"
        r.error = str(e)[:200]
    return r


async def _run_method_async(name: str, mode: str, layer: str, fn: Callable) -> MethodResult:
    """Execute async method (handles sync properties via isawaitable)."""
    r = MethodResult(name=name, mode=mode, layer=layer)
    t0 = time.time()
    try:
        result = fn()
        data = await result if inspect.isawaitable(result) else result
        r.elapsed = round(time.time() - t0, 2)
        r.status = "none" if data is None else "ok"
        s = _summarize(data)
        r.data_type, r.data_keys, r.data_count, r.data_sample = s["data_type"], s["data_keys"], s["data_count"], s["data_sample"]
        r.raw_data = data
    except Exception as e:
        r.elapsed = round(time.time() - t0, 2)
        r.status = "error"
        r.error = str(e)[:200]
    return r


def _print_result(r: MethodResult):
    icon = {"ok": "✅", "none": "⚪", "error": "❌", "skip": "⏭️"}.get(r.status, "?")
    dt = f"{r.data_type}[{r.data_count}]"
    print(f"  {icon} [{r.mode:5s}] {r.name:35s} {r.elapsed:5.1f}s  {dt:15s}", end="")
    if r.status == "error":
        print(f"  ERR: {r.error[:50]}")
    elif r.status == "ok" and r.data_keys:
        print(f"  keys: {r.data_keys[:5]}{'...' if len(r.data_keys) > 5 else ''}")
    elif r.status == "ok" and r.data_type == "list":
        print(f"  items: {r.data_count}")
    else:
        print()


def _skip_msg(mode, name, reason):
    print(f"  ⏭️ [{mode:5s}] {name:35s}  SKIP ({reason})")


def _can_run(entry, ctx):
    if entry["needs_user_id"] and not ctx["user_id"]:
        return False, "no user_id"
    if entry["needs_shortcode"] and not ctx["shortcode"]:
        return False, "no shortcode"
    if entry["needs_media_id"] and not ctx["media_id"]:
        return False, "no media_id"
    return True, ""


def _get_api(entry, public_api, anon_client):
    return public_api if entry["layer"] == "public" else anon_client


def _build_context(ig_public, username, hashtag, location_id):
    """Build context: extract user_id, shortcode, media_id from profile."""
    ctx = {"username": username, "hashtag": hashtag, "location_id": location_id,
           "user_id": None, "shortcode": None, "media_id": None}
    print("\n🔍 Context: user_id, shortcode, media_id ...")
    try:
        profile = ig_public.get_profile(username)
        if profile:
            ctx["user_id"] = profile.get("user_id") or profile.get("pk")
            posts = profile.get("recent_posts", [])
            if posts:
                ctx["shortcode"] = posts[0].get("shortcode") or posts[0].get("code")
                ctx["media_id"] = posts[0].get("pk") or posts[0].get("id")
            print(f"  ✅ user_id   = {ctx['user_id']}")
            print(f"  ✅ shortcode = {ctx['shortcode']}")
            print(f"  ✅ media_id  = {ctx['media_id']}")
    except Exception as e:
        print(f"  ⚠️ Context error: {e}")
    return ctx


async def _build_context_async(ig_public, username, hashtag, location_id):
    """Async context builder."""
    ctx = {"username": username, "hashtag": hashtag, "location_id": location_id,
           "user_id": None, "shortcode": None, "media_id": None}
    print("\n🔍 Async context: user_id, shortcode, media_id ...")
    try:
        profile = await ig_public.get_profile(username)
        if profile:
            ctx["user_id"] = profile.get("user_id") or profile.get("pk")
            posts = profile.get("recent_posts", [])
            if posts:
                ctx["shortcode"] = posts[0].get("shortcode") or posts[0].get("code")
                ctx["media_id"] = posts[0].get("pk") or posts[0].get("id")
            print(f"  ✅ user_id   = {ctx['user_id']}")
            print(f"  ✅ shortcode = {ctx['shortcode']}")
            print(f"  ✅ media_id  = {ctx['media_id']}")
    except Exception as e:
        print(f"  ⚠️ Async context error: {e}")
    return ctx


def _print_summary(all_results, layer_filter=None, method_filter=None):
    """Print summary table."""
    print(f"\n{'═' * 70}")
    print("  RESULTS SUMMARY")
    print(f"{'═' * 70}")

    sync_map = {r.name: r for r in all_results if r.mode == "sync"}
    async_map = {r.name: r for r in all_results if r.mode == "async"}

    layers = {}
    for entry in REGISTRY:
        if method_filter and method_filter not in entry["name"]:
            continue
        if layer_filter and layer_filter not in entry["layer"]:
            continue
        key = (entry["layer"], entry["category"])
        if key not in layers:
            layers[key] = []
        layers[key].append(entry["name"])

    stats = {"sync_ok": 0, "sync_err": 0, "sync_none": 0,
             "async_ok": 0, "async_err": 0, "async_none": 0,
             "parity_match": 0, "parity_total": 0}

    for (layer, cat), names in layers.items():
        print(f"\n  📦 [{layer.upper():10s}] {cat.upper()}")
        for name in names:
            s = sync_map.get(name)
            a = async_map.get(name)
            s_icon = {"ok": "✅", "none": "⚪", "error": "❌"}.get(s.status, "⏭️") if s else "  "
            a_icon = {"ok": "✅", "none": "⚪", "error": "❌"}.get(a.status, "⏭️") if a else "  "
            s_time = f"{s.elapsed:.1f}s" if s else "  -  "
            a_time = f"{a.elapsed:.1f}s" if a else "  -  "
            match_icon = ""
            if s and a:
                stats["parity_total"] += 1
                if s.status == a.status:
                    stats["parity_match"] += 1
                    match_icon = "=="
                else:
                    match_icon = "!!"
            if s:
                stats[f"sync_{s.status}"] = stats.get(f"sync_{s.status}", 0) + 1
            if a:
                stats[f"async_{a.status}"] = stats.get(f"async_{a.status}", 0) + 1
            print(f"    {name:35s} {s_icon} {s_time:>6s}  {a_icon} {a_time:>6s}  {match_icon}")

    print(f"\n  {'─' * 60}")
    print(f"  Sync:  ✅ {stats['sync_ok']}  ⚪ {stats['sync_none']}  ❌ {stats['sync_err']}")
    print(f"  Async: ✅ {stats['async_ok']}  ⚪ {stats['async_none']}  ❌ {stats['async_err']}")
    if stats["parity_total"] > 0:
        pct = 100 * stats["parity_match"] / stats["parity_total"]
        print(f"  Parity: {stats['parity_match']}/{stats['parity_total']} ({pct:.0f}%)")
    print(f"  Total: {len(all_results)} method calls")
    return stats


# ═══════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════

def run_diagnostics(
    ig,
    username: str = "cristiano",
    hashtag: str = "fashion",
    location_id: str = "213385402",
    method_filter: Optional[str] = None,
    layer_filter: Optional[str] = None,
    sync_only: bool = False,
    async_only: bool = False,
    output_dir: Optional[str] = None,
) -> List[MethodResult]:
    """
    Run full diagnostics on all public anonymous API methods.

    Args:
        ig: Instagram or AsyncInstagram instance (anonymous mode recommended)
        username: Target username for profile/content tests
        hashtag: Target hashtag for hashtag tests
        location_id: Target location ID for location tests
        method_filter: Only test methods containing this substring
        layer_filter: "public" or "low" to filter by layer
        sync_only: Only run sync tests
        async_only: Only run async tests
        output_dir: Directory for JSON output files (optional)

    Returns:
        List of MethodResult objects

    Usage:
        from instaharvest_v2 import Instagram
        from instaharvest_v2.diagnostics import run_diagnostics

        ig = Instagram.anonymous(unlimited=True)
        ig.add_proxy("http://proxy:port")
        results = run_diagnostics(ig, username="cristiano")
    """
    total = len([e for e in REGISTRY
                 if (not method_filter or method_filter in e["name"])
                 and (not layer_filter or layer_filter in e["layer"])])

    print("═" * 70)
    print("  🔬 InstaHarvest v2 — Diagnostics")
    print(f"  Username: @{username} | Hashtag: #{hashtag} | Location: {location_id}")
    print(f"  Methods: {total} | Layer: {layer_filter or 'ALL'}")
    print("═" * 70)

    all_results: List[MethodResult] = []
    anon_client = ig._anon_client

    # ── SYNC ──
    if not async_only:
        ctx = _build_context(ig.public, username, hashtag, location_id)

        for layer_name, label in [("public", "PUBLIC API"), ("low-level", "LOW-LEVEL ANON CLIENT")]:
            if layer_filter and layer_filter not in layer_name:
                continue
            entries = [e for e in REGISTRY if e["layer"] == layer_name]
            if not entries:
                continue
            print(f"\n{'─' * 70}")
            print(f"  SYNC — {label} ({len(entries)} methods)")
            print(f"{'─' * 70}")
            for entry in entries:
                if method_filter and method_filter not in entry["name"]:
                    continue
                can, reason = _can_run(entry, ctx)
                if not can:
                    _skip_msg("sync", entry["name"], reason)
                    continue
                api = _get_api(entry, ig.public, anon_client)
                fn = entry["fn_builder"](api, ctx)
                r = _run_method(entry["name"], "sync", entry["layer"], fn)
                _print_result(r)
                all_results.append(r)

    # ── ASYNC ──
    if not sync_only:
        async def _run_async():
            from .async_instagram import AsyncInstagram
            ig_async = AsyncInstagram.anonymous(unlimited=True)
            # Copy proxies from sync instance
            try:
                for url in ig._proxy_mgr._proxies.keys():
                    ig_async.add_proxy(url)
            except Exception:
                pass  # no proxies configured
            anon_async = ig_async._anon_client

            if async_only:
                ctx_a = await _build_context_async(ig_async.public, username, hashtag, location_id)
            else:
                ctx_a = ctx  # reuse sync context

            results = []
            for layer_name, label in [("public", "PUBLIC API"), ("low-level", "LOW-LEVEL ANON CLIENT")]:
                if layer_filter and layer_filter not in layer_name:
                    continue
                entries = [e for e in REGISTRY if e["layer"] == layer_name]
                if not entries:
                    continue
                print(f"\n{'─' * 70}")
                print(f"  ASYNC — {label} ({len(entries)} methods)")
                print(f"{'─' * 70}")
                for entry in entries:
                    if method_filter and method_filter not in entry["name"]:
                        continue
                    can, reason = _can_run(entry, ctx_a)
                    if not can:
                        _skip_msg("async", entry["name"], reason)
                        continue
                    api = _get_api(entry, ig_async.public, anon_async)
                    fn = entry["fn_builder"](api, ctx_a)
                    r = await _run_method_async(entry["name"], "async", entry["layer"], fn)
                    _print_result(r)
                    results.append(r)
            return results

        async_results = asyncio.run(_run_async())
        all_results.extend(async_results)

    # ── Summary ──
    stats = _print_summary(all_results, layer_filter, method_filter)

    # ── JSON Output ──
    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, "diagnostics_results.json")
        full_path = os.path.join(output_dir, "diagnostics_full_data.json")

        summary = {
            "username": username, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "stats": stats, "results": {},
        }
        full_data = {}
        for r in all_results:
            key = f"{r.mode}_{r.name}"
            summary["results"][key] = {
                "layer": r.layer, "status": r.status, "elapsed": r.elapsed,
                "data_type": r.data_type, "data_count": r.data_count,
                "data_keys": r.data_keys, "data_sample": r.data_sample,
                "error": r.error or None,
            }
            if r.raw_data is not None:
                full_data[key] = r.raw_data

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  💾 Summary: {summary_path}")
        print(f"  💾 Full data: {full_path}")

    return all_results


def get_registered_methods() -> List[dict]:
    """Return list of all registered diagnostic methods.

    Returns:
        List of dicts with keys: name, layer, category, needs_user_id,
        needs_shortcode, needs_media_id
    """
    return [
        {k: v for k, v in entry.items() if k != "fn_builder"}
        for entry in REGISTRY
    ]
