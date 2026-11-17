"""
Architectural Hardening & Regression Tests
==========================================
Verifies transport `.request()` normalization, sync/async sub-API contract parity,
lazy-loading parity on `AsyncInstagram`, non-blocking async AST invariants,
and safe outside-loop initialization for high-level async orchestrators.
"""

import ast
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from instaharvest_v2.async_client import AsyncHttpClient
from instaharvest_v2.async_instagram import AsyncInstagram
from instaharvest_v2.client import HttpClient
from instaharvest_v2.config import API_BASE, BASE_URL
from instaharvest_v2.http_utils import maybe_await, normalize_api_url


PKG_ROOT = Path(__file__).resolve().parent.parent / "instaharvest_v2"


# ═══════════════════════════════════════════════════════════
# 1. URL Normalization & Client.request() Contracts
# ═══════════════════════════════════════════════════════════


class TestHttpRequestContract:
    def test_normalize_api_url_handles_relative_api_v1_and_full(self):
        assert normalize_api_url("/users/1/info/") == f"{API_BASE}/users/1/info/"
        assert normalize_api_url("users/1/info/") == f"{API_BASE}/users/1/info/"
        # Must NOT produce double /api/v1/api/v1
        assert normalize_api_url("/api/v1/tags/python/info/") == f"{BASE_URL}/api/v1/tags/python/info/"
        assert normalize_api_url("https://www.instagram.com/graphql/query") == "https://www.instagram.com/graphql/query"
        assert normalize_api_url("/ignored/", full_url="https://example.com/custom") == "https://example.com/custom"
        assert normalize_api_url("") == API_BASE

    def test_sync_http_client_request_delegates_with_normalized_url(self):
        client = HttpClient.__new__(HttpClient)
        client._request = MagicMock(return_value={"status": "ok"})

        res_get = client.request("get", "/api/v1/feed/timeline/", params={"max_id": "123"})
        assert res_get == {"status": "ok"}
        client._request.assert_called_with(
            "GET",
            f"{BASE_URL}/api/v1/feed/timeline/",
            params={"max_id": "123"},
            data=None,
            rate_category="get_default",
            session=None,
        )

        res_post = client.request("POST", "/tags/python/sections/", data={"tab": "recent"})
        assert res_post == {"status": "ok"}
        client._request.assert_called_with(
            "POST",
            f"{API_BASE}/tags/python/sections/",
            params=None,
            data={"tab": "recent"},
            rate_category="post_default",
            session=None,
        )

    def test_async_http_client_request_delegates_with_normalized_url(self):
        aclient = AsyncHttpClient.__new__(AsyncHttpClient)
        aclient._request = AsyncMock(return_value={"status": "ok"})

        async def _run():
            res = await aclient.request(
                "post",
                "/api/v1/tags/instaharvest/sections/",
                data={"tab": "top"},
                rate_category="get_feed",
            )
            assert res == {"status": "ok"}

        asyncio.run(_run())
        aclient._request.assert_awaited_once_with(
            "POST",
            f"{BASE_URL}/api/v1/tags/instaharvest/sections/",
            params=None,
            data={"tab": "top"},
            rate_category="get_feed",
            session=None,
        )


# ═══════════════════════════════════════════════════════════
# 2. Sub-API Method Contract Parity (Strict autospec + Real)
# ═══════════════════════════════════════════════════════════


class TestSubAPIContractParity:
    def test_upload_and_async_upload_aliases(self):
        from instaharvest_v2.api.async_upload import AsyncUploadAPI
        from instaharvest_v2.api.upload import UploadAPI

        for cls in (UploadAPI, AsyncUploadAPI):
            spec = create_autospec(cls, instance=True)
            for m in ("photo", "video", "reel", "post_photo", "post_video", "post_reel"):
                assert callable(getattr(spec, m))

        sync_api = UploadAPI(create_autospec(HttpClient, instance=True))
        sync_api.post_photo = MagicMock(return_value={"pk": "1"})
        sync_api.post_video = MagicMock(return_value={"pk": "2"})
        sync_api.post_reel = MagicMock(return_value={"pk": "3"})
        assert sync_api.photo("a.jpg", caption="hi") == {"pk": "1"}
        assert sync_api.video("a.mp4", caption="vid") == {"pk": "2"}
        assert sync_api.reel("r.mp4", caption="reel") == {"pk": "3"}

        async_api = AsyncUploadAPI(create_autospec(AsyncHttpClient, instance=True))
        async_api.post_photo = AsyncMock(return_value={"pk": "1"})
        async_api.post_video = AsyncMock(return_value={"pk": "2"})
        async_api.post_reel = AsyncMock(return_value={"pk": "3"})

        async def _run():
            assert await async_api.photo("a.jpg", caption="hi") == {"pk": "1"}
            assert await async_api.video("a.mp4", caption="vid") == {"pk": "2"}
            assert await async_api.reel("r.mp4", caption="reel") == {"pk": "3"}

        asyncio.run(_run())

    def test_stories_and_async_stories_contracts(self):
        from instaharvest_v2.api.async_stories import AsyncStoriesAPI
        from instaharvest_v2.api.stories import StoriesAPI

        sync_client = create_autospec(HttpClient, instance=True)
        stories = StoriesAPI(sync_client)
        stories.get_highlights_tray = MagicMock(return_value={"tray": []})
        assert stories.get_highlights(123) == {"tray": []}
        stories.get_highlights_tray.assert_called_once_with(123)

        with patch("instaharvest_v2.api.upload.UploadAPI.post_story_photo", return_value={"status": "ok"}) as m_up:
            assert stories.upload_photo(image_data=b"img") == {"status": "ok"}
            m_up.assert_called_once_with(image_path=None, image_data=b"img")

        async_client = create_autospec(AsyncHttpClient, instance=True)
        astories = AsyncStoriesAPI(async_client)
        astories.get_highlights_tray = AsyncMock(return_value={"tray": []})

        async def _run():
            assert await astories.get_highlights(456) == {"tray": []}
            astories.get_highlights_tray.assert_awaited_once_with(456)
            with patch(
                "instaharvest_v2.api.async_upload.AsyncUploadAPI.post_story_photo",
                new=AsyncMock(return_value={"status": "ok"}),
            ) as m_aup:
                assert await astories.upload_photo(image_data=b"img") == {"status": "ok"}
                m_aup.assert_awaited_once_with(image_path=None, image_data=b"img")

        asyncio.run(_run())

    def test_hashtags_and_async_hashtags_sections_and_recent(self):
        from instaharvest_v2.api.async_hashtags import AsyncHashtagsAPI
        from instaharvest_v2.api.hashtags import HashtagsAPI

        sync_client = create_autospec(HttpClient, instance=True)
        sync_client.post.return_value = {"sections": [{"id": "s1"}]}
        ht = HashtagsAPI(sync_client)
        res = ht.get_recent_media("#python", max_id="cur1")
        assert res == {"sections": [{"id": "s1"}]}
        sync_client.post.assert_called_once_with(
            "/tags/python/sections/",
            data={"tab": "recent", "max_id": "cur1"},
            rate_category="get_feed",
        )

        async_client = create_autospec(AsyncHttpClient, instance=True)
        async_client.post = AsyncMock(return_value={"sections": [{"id": "s2"}]})
        aht = AsyncHashtagsAPI(async_client)

        async def _run():
            ares = await aht.get_recent_media("#python", max_id="cur2")
            assert ares == {"sections": [{"id": "s2"}]}
            async_client.post.assert_awaited_once_with(
                "/tags/python/sections/",
                data={"tab": "recent", "max_id": "cur2"},
                rate_category="get_feed",
            )

        asyncio.run(_run())

    def test_download_url_to_file_real_async_client(self, tmp_path):
        from instaharvest_v2.api.async_download import AsyncDownloadAPI
        from instaharvest_v2.api.download import DownloadAPI

        # Sync contract
        sync_client = create_autospec(HttpClient, instance=True)
        dl = DownloadAPI(sync_client)
        dl._download_url = MagicMock(return_value="out.jpg")
        assert dl.url_to_file("https://example.com/a.jpg", "out.jpg") == "out.jpg"

        # Async contract backed by real AsyncHttpClient subclass / instance (uses _get_async_session)
        aclient = AsyncHttpClient.__new__(AsyncHttpClient)
        fake_session = MagicMock()
        fake_resp = MagicMock(status_code=200, content=b"JPEGDATA")
        fake_session.get = AsyncMock(return_value=fake_resp)
        aclient._get_async_session = MagicMock(return_value=fake_session)
        fake_sess_mgr = MagicMock()
        fake_sess_mgr.get_session.return_value = MagicMock(user_agent="TestUA/1.0")
        aclient._session_mgr = fake_sess_mgr

        adl = AsyncDownloadAPI(aclient)
        assert adl._is_async_client() is True
        target = tmp_path / "pic.jpg"

        async def _run():
            saved = await adl.url_to_file("https://example.com/pic.jpg", str(target))
            assert saved == str(target)

        asyncio.run(_run())
        assert target.read_bytes() == b"JPEGDATA"
        aclient._get_async_session.assert_called_once()


# ═══════════════════════════════════════════════════════════
# 3. AsyncInstagram Lazy Loading & Outside-Loop Safety
# ═══════════════════════════════════════════════════════════


class TestAsyncInstagramLazyAndSafety:
    def test_async_instagram_lazy_loading_parity(self):
        ig = AsyncInstagram()
        try:
            assert ig.loaded_modules == []
            assert "users" not in ig.__dict__
            assert "feed" not in ig.__dict__
            assert "batch" not in ig.__dict__
            assert "public_data" not in ig.__dict__
            assert "users" in dir(ig)
            assert "public_data" in dir(ig)

            # Dependency resolution: feed -> graphql
            feed = ig.feed
            assert feed is not None
            assert "graphql" in ig.loaded_modules
            assert "feed" in ig.loaded_modules

            # public_data -> public
            pd = ig.public_data
            assert pd is not None
            assert "public" in ig.loaded_modules
            assert "public_data" in ig.loaded_modules

            # batch
            assert ig.batch._ig is ig

            # Unknown attribute raises AttributeError cleanly
            with pytest.raises(AttributeError):
                _ = ig.non_existent_module_xyz
        finally:
            asyncio.run(ig.close())

    def test_async_scheduler_and_ab_test_init_outside_event_loop(self, tmp_path):
        from instaharvest_v2.api.async_ab_test import AsyncABTestAPI
        from instaharvest_v2.api.async_scheduler import AsyncSchedulerAPI, SchedulerJob

        # Must not raise RuntimeError: no running event loop
        ab = AsyncABTestAPI(MagicMock())
        assert isinstance(ab._tests, dict)

        sched_file = tmp_path / "jobs.json"
        sched = AsyncSchedulerAPI(MagicMock(), MagicMock(), persist_path=str(sched_file))
        job = SchedulerJob("post", datetime(2030, 1, 1), {"photo": "x.jpg"}, job_id="j1")
        sched._jobs.append(job)

        asyncio.run(sched._save_jobs())
        saved = json.loads(sched_file.read_text(encoding="utf-8"))
        assert isinstance(saved, list) and len(saved) == 1
        assert saved[0]["id"] == "j1"
        assert saved[0]["job_type"] == "post"

    def test_agent_package_lazy_exports(self):
        import instaharvest_v2.agent as agent_pkg
        from instaharvest_v2.agent import (
            InstaAgent,
            AgentResult,
            Permission,
            AgentCoordinator,
            CoordinatorResult,
        )
        assert InstaAgent is not None
        assert AgentResult is not None
        assert Permission.FULL_ACCESS is not None
        assert AgentCoordinator is not None
        assert CoordinatorResult is not None
        with pytest.raises(AttributeError):
            _ = agent_pkg.non_existent_agent_symbol


# ═══════════════════════════════════════════════════════════
# 4. Static AST Architectural Invariants
# ═══════════════════════════════════════════════════════════


class TestAsyncASTInvariants:
    def test_no_blocking_sleep_in_async_def(self):
        offenders = []
        for p in sorted(PKG_ROOT.rglob("*.py")):
            tree = ast.parse(p.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    for sub in ast.walk(node):
                        if (
                            isinstance(sub, ast.Call)
                            and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr == "sleep"
                            and isinstance(sub.func.value, ast.Name)
                            and sub.func.value.id in ("time", "_time")
                        ):
                            offenders.append(f"{p.name}:{sub.lineno} ({node.name})")
        assert offenders == [], f"Blocking time.sleep found inside async def: {offenders}"

    def test_no_unawaited_async_subapi_calls_in_async_modules(self):
        # Collect async/sync method map across package
        class_methods = {}
        for p in sorted(PKG_ROOT.rglob("*.py")):
            tree = ast.parse(p.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    for m in node.body:
                        if isinstance(m, ast.AsyncFunctionDef):
                            class_methods.setdefault(node.name, {})[m.name] = "async"
                        elif isinstance(m, ast.FunctionDef):
                            class_methods.setdefault(node.name, {})[m.name] = "sync"

        attr_map = {
            "_client": "AsyncHttpClient",
            "_users": "AsyncUsersAPI",
            "_media": "AsyncMediaAPI",
            "_friendships": "AsyncFriendshipsAPI",
            "_stories": "AsyncStoriesAPI",
            "_graphql": "AsyncGraphQLAPI",
            "_feed": "AsyncFeedAPI",
            "_upload": "AsyncUploadAPI",
            "_download": "AsyncDownloadAPI",
            "_hashtags": "AsyncHashtagsAPI",
            "_direct": "AsyncDirectAPI",
            "_analytics": "AsyncAnalyticsAPI",
            "_hashtag_research": "AsyncHashtagResearchAPI",
            "_public": "AsyncPublicAPI",
            "_anon_client": "AsyncAnonClient",
        }

        def _is_awaited(call_node, parents):
            cur = call_node
            while id(cur) in parents:
                parent = parents[id(cur)]
                if isinstance(parent, ast.Await):
                    return True
                if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name) and parent.func.id in ("maybe_await", "_maybe_await"):
                    cur = parent
                    continue
                if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute) and parent.func.attr in ("gather", "create_task", "wait", "wait_for"):
                    return True
                if isinstance(parent, (ast.List, ast.Tuple, ast.Starred, ast.ListComp)):
                    cur = parent
                    continue
                break
            return False

        missing_methods = []
        unawaited = []
        for p in sorted((PKG_ROOT / "api").glob("async_*.py")):
            mapping = dict(attr_map)
            if p.name == "async_public.py":
                mapping["_client"] = "AsyncAnonClient"
            src = p.read_text(encoding="utf-8")
            lines = src.splitlines()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                parents = {id(c): par for par in ast.walk(node) for c in ast.iter_child_nodes(par)}
                for sub in ast.walk(node):
                    if not isinstance(sub, ast.Call):
                        continue
                    fn = sub.func
                    if (
                        isinstance(fn, ast.Attribute)
                        and isinstance(fn.value, ast.Attribute)
                        and isinstance(fn.value.value, ast.Name)
                        and fn.value.value.id == "self"
                    ):
                        cls_name = mapping.get(fn.value.attr)
                        if not cls_name or cls_name not in class_methods:
                            continue
                        kind = class_methods[cls_name].get(fn.attr)
                        if kind is None:
                            ctx = "\n".join(lines[max(0, sub.lineno - 3):sub.lineno])
                            if f'hasattr(self.{fn.value.attr}, "{fn.attr}")' in ctx:
                                continue
                            missing_methods.append(f"{p.name}:{sub.lineno} self.{fn.value.attr}.{fn.attr} -> {cls_name}")
                        elif kind == "async" and not _is_awaited(sub, parents):
                            unawaited.append(f"{p.name}:{sub.lineno} self.{fn.value.attr}.{fn.attr}")

        assert missing_methods == [], f"Missing methods called on async clients/APIs: {missing_methods}"
        assert unawaited == [], f"Unawaited async sub-API calls: {unawaited}"
