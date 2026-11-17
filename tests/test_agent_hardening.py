"""
Agent & AsyncHardening Regression Tests
========================================
Strict contract tests using create_autospec against real API classes,
AST signature verification across agent tools & knowledge.py,
AsyncInstagram anonymous support, SafeExecutor top-level await, and
multi-turn provider message formatting.
"""

import ast
import inspect
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, create_autospec, PropertyMock

import pytest

from instaharvest_v2 import Instagram, AsyncInstagram
from instaharvest_v2.agent import InstaAgent, Permission
from instaharvest_v2.agent.executor import SafeExecutor
from instaharvest_v2.agent.knowledge import SYSTEM_PROMPT
from instaharvest_v2.agent.providers.base import ProviderResponse, ToolCall, instaharvest_v2_TOOLS
from instaharvest_v2.agent.providers.claude_provider import ClaudeProvider
from instaharvest_v2.agent.providers.gemini_provider import GeminiProvider
from instaharvest_v2.agent.tools import TOOL_HANDLERS
from instaharvest_v2.api.ab_test import ABTestAPI
from instaharvest_v2.api.audience import AudienceAPI
from instaharvest_v2.api.automation import AutomationAPI
from instaharvest_v2.api.comment_manager import CommentManagerAPI
from instaharvest_v2.api.export import ExportAPI
from instaharvest_v2.api.feed import FeedAPI
from instaharvest_v2.api.growth import GrowthAPI
from instaharvest_v2.api.monitor import AccountWatcher, MonitorAPI
from instaharvest_v2.api.pipeline import PipelineAPI
from instaharvest_v2.api.scheduler import SchedulerAPI
from instaharvest_v2.api.search import SearchAPI
from instaharvest_v2.api.stories import StoriesAPI
from instaharvest_v2.api.media import MediaAPI
from instaharvest_v2.api.public import PublicAPI


def _make_strict_ig():
    """Build a strict mock Instagram object backed by real API signatures."""
    ig = MagicMock()
    ig.automation = create_autospec(AutomationAPI, instance=True)
    ig.scheduler = create_autospec(SchedulerAPI, instance=True)
    ig.monitor = create_autospec(MonitorAPI, instance=True)
    ig.export = create_autospec(ExportAPI, instance=True)
    ig.pipeline = create_autospec(PipelineAPI, instance=True)
    ig.growth = create_autospec(GrowthAPI, instance=True)
    ig.audience = create_autospec(AudienceAPI, instance=True)
    ig.ab_test = create_autospec(ABTestAPI, instance=True)
    ig.comment_manager = create_autospec(CommentManagerAPI, instance=True)
    ig.feed = create_autospec(FeedAPI, instance=True)
    ig.search = create_autospec(SearchAPI, instance=True)
    ig.stories = create_autospec(StoriesAPI, instance=True)
    ig.media = create_autospec(MediaAPI, instance=True)
    ig.public = create_autospec(PublicAPI, instance=True)
    return ig


class TestToolHandlerStrictSignatures:
    """Invoke every fixed handler with create_autospec to forbid signature drift."""

    def test_automation_handlers_strict_signatures(self):
        ig = _make_strict_ig()
        ig.automation.dm_new_followers.return_value = {"sent": 2}
        ig.automation.comment_on_hashtag.return_value = {"commented": 1}
        ig.automation.auto_like_feed.return_value = {"liked": 3}
        ig.automation.auto_like_hashtag.return_value = {"liked": 2}
        ig.automation.watch_stories.return_value = {"watched": 4, "username": "alice"}
        ig.stories.get_reels_tray.return_value = {
            "tray": [{"user": {"username": "alice"}}, {"user": {"username": "bob"}}]
        }

        res1 = json.loads(TOOL_HANDLERS["auto_dm_new_followers"]({"message": "hi", "max_count": 3}, ig=ig, is_logged_in=True))
        assert res1["sent"] == 2
        ig.automation.dm_new_followers.assert_called_once_with(templates="hi", max_count=3)

        res2 = json.loads(TOOL_HANDLERS["auto_comment_hashtag"]({"hashtag": "py", "comment": "nice", "max_count": 2}, ig=ig, is_logged_in=True))
        assert res2["commented"] == 1
        ig.automation.comment_on_hashtag.assert_called_once_with(tag="py", templates=["nice"], count=2)

        res3 = json.loads(TOOL_HANDLERS["auto_like_feed"]({"max_count": 5}, ig=ig, is_logged_in=True))
        assert res3["liked"] == 3
        ig.automation.auto_like_feed.assert_called_once_with(count=5)

        res4 = json.loads(TOOL_HANDLERS["auto_like_hashtag"]({"hashtag": "code", "max_count": 4}, ig=ig, is_logged_in=True))
        assert res4["liked"] == 2
        ig.automation.auto_like_hashtag.assert_called_once_with(tag="code", count=4)

        # watch_stories with explicit username
        res5 = json.loads(TOOL_HANDLERS["auto_watch_stories"]({"username": "@alice"}, ig=ig, is_logged_in=True))
        assert res5["watched"] == 4
        ig.automation.watch_stories.assert_called_with("alice")

        # watch_stories without username falls back to tray
        res6 = json.loads(TOOL_HANDLERS["auto_watch_stories"]({"max_count": 2}, ig=ig, is_logged_in=True))
        assert res6["accounts"] == ["alice", "bob"]
        assert res6["watched"] == 8

    def test_action_log_and_monitor_event_log_properties(self):
        ig = _make_strict_ig()
        type(ig.automation).action_log = PropertyMock(return_value=[{"action": "like", "target": "x"}])
        res = json.loads(TOOL_HANDLERS["get_action_log"]({}, ig=ig, is_logged_in=True))
        assert isinstance(res, list) and res[0]["action"] == "like"

        type(ig.monitor).event_log = PropertyMock(return_value=[
            {"username": "alice", "event": "new_post"},
            {"username": "bob", "event": "bio_change"},
        ])
        all_ev = json.loads(TOOL_HANDLERS["get_monitor_events"]({}, ig=ig, is_logged_in=True))
        assert len(all_ev) == 2
        alice_ev = json.loads(TOOL_HANDLERS["get_monitor_events"]({"username": "@alice"}, ig=ig, is_logged_in=True))
        assert len(alice_ev) == 1 and alice_ev[0]["username"] == "alice"

        watcher = AccountWatcher("alice")
        ig.monitor.watch.return_value = watcher
        type(ig.monitor).watched_accounts = PropertyMock(return_value=["alice"])
        mon = json.loads(TOOL_HANDLERS["monitor_account"]({"username": "alice"}, ig=ig, is_logged_in=True))
        assert mon == {"watching": "alice", "status": "watching", "watched_accounts": ["alice"]}

    def test_scheduler_handlers_strict_signatures(self):
        ig = _make_strict_ig()
        ig.scheduler.post_at.return_value = {"id": "p1"}
        ig.scheduler.story_at.return_value = {"id": "s1"}
        ig.scheduler.reel_at.return_value = {"id": "r1"}

        p = json.loads(TOOL_HANDLERS["schedule_post"](
            {"image_path": "img.jpg", "caption": "cap", "schedule_time": "in 1 hour"}, ig=ig, is_logged_in=True
        ))
        assert p["id"] == "p1"
        ig.scheduler.post_at.assert_called_once_with(scheduled_time="in 1 hour", photo="img.jpg", caption="cap")

        s_photo = json.loads(TOOL_HANDLERS["schedule_story"](
            {"media_path": "story.png", "schedule_time": "in 1 hour"}, ig=ig, is_logged_in=True
        ))
        assert s_photo["id"] == "s1"
        ig.scheduler.story_at.assert_called_with(scheduled_time="in 1 hour", photo="story.png")

        s_vid = json.loads(TOOL_HANDLERS["schedule_story"](
            {"media_path": "story.mp4", "schedule_time": "in 2 hours"}, ig=ig, is_logged_in=True
        ))
        assert s_vid["id"] == "s1"
        ig.scheduler.story_at.assert_called_with(scheduled_time="in 2 hours", video="story.mp4")

        r = json.loads(TOOL_HANDLERS["schedule_reel"](
            {"video_path": "reel.mp4", "caption": "r", "schedule_time": "in 3 hours"}, ig=ig, is_logged_in=True
        ))
        assert r["id"] == "r1"
        ig.scheduler.reel_at.assert_called_once_with(scheduled_time="in 3 hours", video="reel.mp4", caption="r")

    def test_export_and_pipeline_handlers(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ig = _make_strict_ig()
        ig.export.followers_to_csv.return_value = {"exported": 5}
        ig.export.following_to_csv.return_value = {"exported": 4}
        ig.export.post_likers.return_value = {"exported": 3}
        ig.export.to_json.return_value = {"file": "u.json"}
        ig.pipeline.to_sqlite.return_value = {"rows_inserted": 2}
        ig.pipeline.to_jsonl.return_value = {"file": "u.jsonl"}

        assert "✅" in TOOL_HANDLERS["export_followers_csv"]({"username": "alice", "filename": "f.csv", "max_count": 50}, ig=ig, is_logged_in=True)
        ig.export.followers_to_csv.assert_called_once_with("alice", output_path="f.csv", max_count=50)

        assert "✅" in TOOL_HANDLERS["export_following_csv"]({"username": "alice", "filename": "g.csv", "max_count": 40}, ig=ig, is_logged_in=True)
        ig.export.following_to_csv.assert_called_once_with("alice", output_path="g.csv", max_count=40)

        assert "✅" in TOOL_HANDLERS["export_post_likers"]({"media_id": "123", "filename": "l.csv"}, ig=ig, is_logged_in=True)
        ig.export.post_likers.assert_called_once_with("123", output_path="l.csv")

        # Username delegation mode
        assert "✅" in TOOL_HANDLERS["export_to_json"]({"data": "@alice", "filename": "alice.json"}, ig=ig)
        ig.export.to_json.assert_called_once_with("alice", output_path="alice.json")
        assert "✅" in TOOL_HANDLERS["save_to_sqlite"]({"data": "@alice", "db_name": "alice.db"}, ig=ig)
        ig.pipeline.to_sqlite.assert_called_once_with("alice", db_path="alice.db")
        assert "✅" in TOOL_HANDLERS["save_to_jsonl"]({"data": "@alice", "filename": "alice.jsonl"}, ig=ig)
        ig.pipeline.to_jsonl.assert_called_once_with("alice", output_path="alice.jsonl")

        # Structured inline JSON mode
        payload = json.dumps([{"username": "a", "followers": 10}, {"username": "b", "followers": 20}])
        assert "✅" in TOOL_HANDLERS["export_to_json"]({"data": payload, "filename": "raw.json"}, ig=ig)
        assert json.loads((tmp_path / "raw.json").read_text(encoding="utf-8"))[0]["username"] == "a"

        assert "✅" in TOOL_HANDLERS["save_to_jsonl"]({"data": payload, "filename": "raw.jsonl"}, ig=ig)
        lines = (tmp_path / "raw.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        assert "✅" in TOOL_HANDLERS["save_to_sqlite"]({"data": payload, "db_name": "raw.db", "table_name": "users"}, ig=ig)
        conn = sqlite3.connect(tmp_path / "raw.db")
        rows = conn.execute('SELECT username, followers FROM "users"').fetchall()
        conn.close()
        assert rows == [("a", "10"), ("b", "20")]

        # Traversal protection
        assert "Error" in TOOL_HANDLERS["export_to_json"]({"data": payload, "filename": "../escape.json"}, ig=ig)

    def test_analytics_growth_comments_feed_explore_handlers(self):
        ig = _make_strict_ig()
        ig.audience.find_lookalike.return_value = {"similar_users": []}
        ig.ab_test.create.return_value = {"id": "t1", "status": "created"}
        ig.growth.follow_hashtag_users.return_value = {"followed": 2}
        ig.comment_manager.get_comments.return_value = {"comments": []}
        ig.feed.get_timeline.return_value = {"posts": [{"user": {"username": "a"}, "like_count": 5, "code": "X"}]}
        ig.feed.get_saved.return_value = {"posts": [{"user": {"username": "b"}, "like_count": 7, "code": "Y"}]}
        ig.feed.get_liked.return_value = {"posts": [{"user": {"username": "c"}, "like_count": 9, "code": "Z"}]}
        ig.search.explore.return_value = {
            "sectional_items": [{
                "layout_content": {
                    "medias": [{"media": {"user": {"username": "exp"}, "like_count": 42, "code": "EXP1"}}]
                }
            }]
        }

        TOOL_HANDLERS["find_lookalike_audience"]({"username": "alice", "max_count": 15}, ig=ig, is_logged_in=True)
        ig.audience.find_lookalike.assert_called_once_with("alice", count=15)

        ab_res = json.loads(TOOL_HANDLERS["create_ab_test"](
            {"variants": ["Var A", "Var B"], "metric": "likes", "description": "Hook test"},
            ig=ig,
            is_logged_in=True,
        ))
        assert ab_res["id"] == "t1"
        call_kwargs = ig.ab_test.create.call_args.kwargs
        assert call_kwargs["name"] == "Hook test"
        assert isinstance(call_kwargs["variants"], dict)
        assert "Var A" in call_kwargs["variants"]

        TOOL_HANDLERS["follow_hashtag_users"]({"hashtag": "py", "max_count": 3}, ig=ig, is_logged_in=True)
        ig.growth.follow_hashtag_users.assert_called_once_with("py", count=3)

        TOOL_HANDLERS["manage_comments"]({"media_id": "111", "max_count": 25}, ig=ig, is_logged_in=True)
        ig.comment_manager.get_comments.assert_called_once_with("111", count=25)

        assert "@a" in TOOL_HANDLERS["get_timeline"]({"max_count": 5}, ig=ig, is_logged_in=True)
        ig.feed.get_timeline.assert_called_once_with(count=5)
        saved_out = TOOL_HANDLERS["get_saved_posts"]({"max_count": 5}, ig=ig, is_logged_in=True)
        assert "instagram.com/p/Y/" in saved_out and "7" in saved_out
        ig.feed.get_saved.assert_called_once_with(count=5)
        assert "@c" in TOOL_HANDLERS["get_liked_posts"]({"max_count": 5}, ig=ig, is_logged_in=True)
        ig.feed.get_liked.assert_called_once_with(count=5)

        explore_out = TOOL_HANDLERS["explore_feed"]({"max_count": 5}, ig=ig, is_logged_in=True)
        ig.search.explore.assert_called_once_with()
        assert "@exp" in explore_out and "EXP1" in explore_out


class TestAgentASTInvariants:
    """Verify zero API drift across all agent tools, schemas, and knowledge.py."""

    def test_all_tool_calls_match_real_instagram_signatures(self):
        ig = Instagram.anonymous()
        resolved = {}
        for name in dir(ig):
            if not name.startswith("_"):
                try:
                    resolved[name] = type(getattr(ig, name))
                except Exception:
                    pass

        tools_dir = Path(__file__).resolve().parent.parent / "instaharvest_v2" / "agent" / "tools"
        for py_file in sorted(tools_dir.glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    f = node.func
                    if (
                        isinstance(f.value, ast.Attribute)
                        and isinstance(f.value.value, ast.Name)
                        and f.value.value.id == "ig"
                    ):
                        mod, meth = f.value.attr, f.attr
                        cls_obj = resolved.get(mod)
                        assert cls_obj is not None, f"Unknown ig.{mod} at {py_file.name}:{node.lineno}"
                        member = getattr(cls_obj, meth, None)
                        assert member is not None, f"Missing ig.{mod}.{meth} at {py_file.name}:{node.lineno}"
                        assert not isinstance(member, property), f"Property called as method: ig.{mod}.{meth}() at {py_file.name}:{node.lineno}"
                        static_attr = inspect.getattr_static(cls_obj, meth)
                        sig = inspect.signature(member)
                        params = list(sig.parameters.values())
                        if not isinstance(static_attr, staticmethod):
                            params = params[1:]
                        valid_kw = {p.name for p in params if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)}
                        accepts_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
                        if not accepts_kw:
                            for kw in node.keywords:
                                if kw.arg is not None:
                                    assert kw.arg in valid_kw, f"Bad kwarg {kw.arg!r} in ig.{mod}.{meth} at {py_file.name}:{node.lineno}"

    def test_knowledge_prompt_references_exist(self):
        import re
        ig = Instagram.anonymous()
        resolved = {n: type(getattr(ig, n)) for n in dir(ig) if not n.startswith("_")}
        for m in re.finditer(r"ig\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)", SYSTEM_PROMPT):
            mod, meth = m.group(1), m.group(2)
            assert mod in resolved, f"SYSTEM_PROMPT unknown mod ig.{mod}.{meth}"
            assert hasattr(resolved[mod], meth), f"SYSTEM_PROMPT missing method ig.{mod}.{meth}"


class TestAsyncAndProviderFixes:
    """Verify AsyncInstagram.anonymous, SafeExecutor await, AutomationAPI.watch_stories, and provider history."""

    def test_async_instagram_anonymous_and_agent_detection(self):
        async_ig = AsyncInstagram.anonymous()
        assert async_ig.public is not None
        agent = InstaAgent(ig=async_ig, provider="ollama")
        assert agent._mode == "async"
        assert agent._is_logged_in is False

    def test_safe_executor_supports_top_level_await(self):
        executor = SafeExecutor(timeout=10)
        res = executor.run("""
async def _fetch():
    return 42

val = await _fetch()
result = val
print(f"got={val}")
""")
        assert res.success, res.error
        assert "got=42" in res.output
        assert res.return_value == 42

    def test_automation_watch_stories_calls_mark_seen_with_list(self):
        stories = create_autospec(StoriesAPI, instance=True)
        stories.get_user_stories.return_value = {"items": [{"pk": "s1", "taken_at": 1700000000}]}
        client = MagicMock()
        client.request.return_value = {"data": {"user": {"pk": "999"}}}
        api = AutomationAPI(
            client=client,
            direct_api=MagicMock(),
            media_api=MagicMock(),
            friendships_api=MagicMock(),
            stories_api=stories,
        )
        res = api.watch_stories("alice")
        assert res["watched"] == 1
        stories.mark_seen.assert_called_once_with([{"media_id": "s1", "user_id": "999", "taken_at": 1700000000}])

    def test_claude_provider_preserves_tool_use_history(self):
        prov = ClaudeProvider(api_key="test-key")
        mock_block = MagicMock(type="text", text="Done")
        prov._client = MagicMock()
        prov._client.messages.create.return_value = MagicMock(content=[mock_block], usage=None)

        agent = InstaAgent(ig=None, provider="ollama")
        agent._provider = prov
        resp = ProviderResponse(
            content="",
            tool_calls=[ToolCall(id="call_123", name="get_profile", arguments={"username": "cristiano"})],
        )
        agent._add_assistant_message(resp)
        agent._add_tool_result(resp.tool_calls[0], '{"followers": 1}')

        prov.generate(agent._history)
        sent = prov._client.messages.create.call_args.kwargs["messages"]
        assistant_msgs = [m for m in sent if m["role"] == "assistant"]
        assert any(isinstance(m["content"], list) and any(b.get("type") == "tool_use" and b.get("id") == "call_123" for b in m["content"]) for m in assistant_msgs)
        tool_result_msgs = [m for m in sent if m["role"] == "user" and isinstance(m["content"], list)]
        assert tool_result_msgs[0]["content"][0]["tool_use_id"] == "call_123"

    def test_auto_execute_does_not_emit_orphan_tool_message(self):
        agent = InstaAgent(ig=None, provider="ollama", permission=Permission.FULL_ACCESS)
        executed = agent._try_auto_execute(
            "Let me compute:\n```python\nprint(1 + 2)\n```",
            MagicMock(),
            None,
            lambda e: None,
        )
        assert executed is True
        assert agent._history[-1]["role"] == "user"
        assert "3" in agent._history[-1]["content"]
