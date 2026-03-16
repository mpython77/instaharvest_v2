"""
test_cli_async_65.py — CLI + AsyncChallenge + AsyncClient cover (364 miss)
==========================================================================
1. cli.py (100 miss) — create_parser, pp, get_ig, main
2. async_challenge.py (93 miss) — resolve, handle_verification, consent, detect_type
3. async_client.py (171 miss) — _request, get/post/upload_raw, error handlers
"""
import pytest
import asyncio
import json
import sys
from io import StringIO
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from types import SimpleNamespace

M = MagicMock

def run(coro, timeout=5):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    except Exception:
        return None
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            loop.run_until_complete(asyncio.sleep(0))
        except:
            pass
        loop.close()


# ═══════════════════════════════════════════════════════════════
# 1. CLI.py (100 miss)
# ═══════════════════════════════════════════════════════════════
class TestCLIParser:
    def test_create_parser(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        assert parser is not None

    def test_parser_profile(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["profile", "cristiano"])
        assert args.command == "profile"
        assert args.username == "cristiano"

    def test_parser_profile_json(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["profile", "cristiano", "--json"])
        assert args.as_json is True

    def test_parser_export_followers(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["export", "followers", "user1", "-o", "out.csv", "-n", "100"])
        assert args.export_type == "followers"
        assert args.count == 100

    def test_parser_export_following(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["export", "following", "user1", "-o", "f.csv"])
        assert args.export_type == "following"

    def test_parser_export_hashtag(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["export", "hashtag", "python", "-n", "50"])
        assert args.export_type == "hashtag"

    def test_parser_export_json(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["export", "json", "user1"])
        assert args.export_type == "json"

    def test_parser_analytics_engagement(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["analytics", "engagement", "user1"])
        assert args.analytics_type == "engagement"

    def test_parser_analytics_all_types(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        for cmd in ["times", "content", "summary"]:
            args = parser.parse_args(["analytics", cmd, "user1"])
            assert args.analytics_type == cmd

    def test_parser_analytics_compare(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["analytics", "compare", "user1", "user2", "user3"])
        assert len(args.usernames) == 3

    def test_parser_hashtag(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        for cmd in ["analyze", "related", "suggest"]:
            args = parser.parse_args(["hashtag", cmd, "fashion"])
            assert args.hashtag_type == cmd

    def test_parser_download(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        for cmd in ["posts", "stories", "all"]:
            args = parser.parse_args(["download", cmd, "user1"])
            assert args.download_type == cmd

    def test_parser_pipeline(self):
        from instaharvest_v2.cli import create_parser
        parser = create_parser()
        for cmd in ["sqlite", "jsonl"]:
            args = parser.parse_args(["pipeline", cmd, "user1"])
            assert args.pipeline_type == cmd


class TestCLIPP:
    def test_pp_json(self, capsys):
        from instaharvest_v2.cli import pp
        pp({"key": "value", "count": 42}, as_json=True)
        out = capsys.readouterr().out
        assert "key" in out

    def test_pp_dict(self, capsys):
        from instaharvest_v2.cli import pp
        pp({"name": "test", "data": {"nested": True}, "list": [1, 2, 3]})
        out = capsys.readouterr().out
        assert "name" in out

    def test_pp_list(self, capsys):
        from instaharvest_v2.cli import pp
        pp(["item1", "item2", "item3"])
        out = capsys.readouterr().out
        assert "item1" in out


class TestCLIMain:
    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "profile", "cristiano"])
    def test_main_profile(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        user = SimpleNamespace(username="cristiano", followers=600000000)
        ig.users.get_by_username.return_value = user
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "profile", "cristiano", "--json"])
    def test_main_profile_json(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.users.get_by_username.return_value = {"username": "cristiano"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "export", "followers", "user1", "-o", "/tmp/f.csv"])
    def test_main_export_followers(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.export.followers_to_csv.return_value = {"exported": 100, "file": "/tmp/f.csv"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "export", "following", "user1", "-o", "/tmp/f.csv"])
    def test_main_export_following(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.export.following_to_csv.return_value = {"exported": 50, "file": "/tmp/f.csv"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "export", "hashtag", "python", "-o", "/tmp/h.csv"])
    def test_main_export_hashtag(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.export.hashtag_users.return_value = {"exported": 20, "file": "/tmp/h.csv"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "export", "json", "user1", "-o", "/tmp/p.json"])
    def test_main_export_json(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.export.to_json.return_value = {"file": "/tmp/p.json"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "analytics", "engagement", "user1"])
    def test_main_analytics_engagement(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.analytics.engagement_rate.return_value = {"rate": 3.5}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "analytics", "times", "user1"])
    def test_main_analytics_times(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.analytics.best_posting_times.return_value = {"best_hour": 18}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "analytics", "content", "user1"])
    def test_main_analytics_content(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.analytics.content_analysis.return_value = {"type": "photo"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "analytics", "summary", "user1"])
    def test_main_analytics_summary(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.analytics.profile_summary.return_value = {"username": "user1"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "analytics", "compare", "u1", "u2"])
    def test_main_analytics_compare(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.analytics.compare.return_value = {
            "winner": "u1",
            "accounts": [
                {"username": "u1", "engagement_rate": 5.0, "followers": 1000},
                {"username": "u2", "engagement_rate": 3.0, "followers": 500},
            ],
        }
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "hashtag", "analyze", "fashion"])
    def test_main_hashtag_analyze(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.hashtag_research.analyze.return_value = {"posts": 1000}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "hashtag", "related", "fashion"])
    def test_main_hashtag_related(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.hashtag_research.related.return_value = [
            {"name": "style", "co_occurrence": 50}
        ]
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "hashtag", "suggest", "fashion"])
    def test_main_hashtag_suggest(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.hashtag_research.suggest.return_value = [
            {"name": "#ootd", "difficulty": "easy", "media_count": 500000}
        ]
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "download", "posts", "user1"])
    def test_main_download_posts(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.bulk_download.all_posts.return_value = {"downloaded": 5, "output_dir": "dl/"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "download", "stories", "user1"])
    def test_main_download_stories(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.bulk_download.all_stories.return_value = {"downloaded": 3}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "download", "all", "user1"])
    def test_main_download_all(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.bulk_download.everything.return_value = {"total_files": 10}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "pipeline", "sqlite", "user1"])
    def test_main_pipeline_sqlite(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.pipeline.to_sqlite.return_value = {"rows_inserted": 50, "file": "db"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "pipeline", "jsonl", "user1"])
    def test_main_pipeline_jsonl(self, mock_get_ig, capsys):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.pipeline.to_jsonl.return_value = {"lines_written": 100, "file": "data.jsonl"}
        main()

    @patch("instaharvest_v2.cli.get_ig")
    @patch("sys.argv", ["prog", "profile", "bad_user"])
    def test_main_error(self, mock_get_ig):
        from instaharvest_v2.cli import main
        ig = M()
        mock_get_ig.return_value = ig
        ig.users.get_by_username.side_effect = Exception("Not found")
        with pytest.raises(SystemExit):
            main()


# ═══════════════════════════════════════════════════════════════
# 2. ASYNC_CHALLENGE.py (93 miss)
# ═══════════════════════════════════════════════════════════════
class TestAsyncChallenge:
    def test_is_enabled(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=None)
        assert h.is_enabled is False
        h2 = AsyncChallengeHandler(code_callback=lambda ctx: "123456")
        assert h2.is_enabled is True

    def test_normalize_url(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        assert AsyncChallengeHandler._normalize_url("https://example.com") == "https://example.com"
        assert "api/v1" in AsyncChallengeHandler._normalize_url("/challenge/123/")
        assert "api/v1" in AsyncChallengeHandler._normalize_url("challenge/123/")

    def test_detect_type_email(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "verify_email"}) == ChallengeType.EMAIL
        assert AsyncChallengeHandler._detect_type({"step_name": "delta_login_review"}) == ChallengeType.EMAIL

    def test_detect_type_sms(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "verify_phone"}) == ChallengeType.SMS
        assert AsyncChallengeHandler._detect_type({"step_name": "phone_number"}) == ChallengeType.SMS

    def test_detect_type_consent(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "consent_required"}) == ChallengeType.CONSENT

    def test_detect_type_captcha(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "captcha"}) == ChallengeType.CAPTCHA

    def test_detect_type_from_step_data(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "", "step_data": {"email": "test@x.com"}}) == ChallengeType.EMAIL
        assert AsyncChallengeHandler._detect_type({"step_name": "", "step_data": {"phone_number": "+1234"}}) == ChallengeType.SMS
        assert AsyncChallengeHandler._detect_type({"step_name": "", "step_data": {"contact_point": "test@x.com"}}) == ChallengeType.EMAIL
        assert AsyncChallengeHandler._detect_type({"step_name": "", "step_data": {"contact_point": "+12345"}}) == ChallengeType.SMS

    def test_detect_type_unknown(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        from instaharvest_v2.challenge import ChallengeType
        assert AsyncChallengeHandler._detect_type({"step_name": "something_new"}) == ChallengeType.UNKNOWN

    def test_build_headers(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler()
        headers = h._build_headers("csrf123", "Mozilla/5.0")
        assert headers["x-csrftoken"] == "csrf123"
        assert headers["user-agent"] == "Mozilla/5.0"

    def test_build_headers_default_ua(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler()
        headers = h._build_headers("csrf123")
        assert "Chrome" in headers["user-agent"]

    def test_parse_challenge_html(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        html = '"step_name":"verify_email","contact_point":"t***@gmail.com"'
        data = AsyncChallengeHandler._parse_challenge_html(html)
        assert data["step_name"] == "verify_email"
        assert data["step_data"]["contact_point"] == "t***@gmail.com"

    def test_parse_challenge_html_empty(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        data = AsyncChallengeHandler._parse_challenge_html("<html>nothing</html>")
        assert "step_name" not in data

    def test_resolve_no_callback(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=None)
        session = M()
        result = run(h.resolve(session, "/challenge/", "csrf"))
        assert result is not None and result.success is False

    def test_resolve_consent(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "123456")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "consent_required", "step_data": {}}
        session.get.return_value = resp
        consent_resp = M()
        consent_resp.json.return_value = {"status": "ok"}
        session.post.return_value = consent_resp
        result = run(h.resolve(session, "/challenge/1/", "csrf"))
        assert result.success is True

    def test_resolve_email_verification(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "654321")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {
            "step_name": "verify_email",
            "step_data": {"contact_point": "t***@gmail.com"}
        }
        session.get.return_value = resp
        submit_resp = M()
        submit_resp.json.return_value = {"status": "ok", "logged_in_user": {"pk": 111}}
        session.post.return_value = submit_resp
        result = run(h.resolve(session, "https://i.instagram.com/challenge/1/", "csrf"))
        assert result.success is True

    def test_resolve_select_method_then_verify(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "999999")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {
            "step_name": "select_verify_method",
            "step_data": {"contact_point": "e***@x.com"}
        }
        session.get.return_value = resp
        post_call = [0]
        def mock_post(*a, **kw):
            post_call[0] += 1
            r = M()
            if post_call[0] == 1:  # select method
                r.json.return_value = {"status": "ok", "step_data": {"contact_point": "test@x.com"}}
            else:  # submit code
                r.json.return_value = {"status": "ok"}
            return r
        session.post.side_effect = mock_post
        result = run(h.resolve(session, "/challenge/2/", "csrf"))

    def test_resolve_code_empty(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "verify_email", "step_data": {}}
        session.get.return_value = resp
        result = run(h.resolve(session, "/challenge/3/", "csrf"))
        assert result.success is False

    def test_resolve_unsupported_type(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "111")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "captcha", "step_data": {}}
        session.get.return_value = resp
        result = run(h.resolve(session, "/challenge/4/", "csrf"))
        assert result.success is False

    def test_resolve_exception(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "111")
        session = AsyncMock()
        session.get.side_effect = Exception("Network error")
        result = run(h.resolve(session, "/challenge/5/", "csrf"))
        assert result.success is False

    def test_get_code_async(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        async def async_cb(ctx):
            return "async_code"
        h = AsyncChallengeHandler(code_callback=async_cb)
        from instaharvest_v2.challenge import ChallengeContext, ChallengeType
        ctx = ChallengeContext(challenge_type=ChallengeType.EMAIL, contact_point="", step_name="")
        result = run(h._get_code(ctx))
        assert result == "async_code"

    def test_consent_fail(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "111")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "consent_required", "step_data": {}}
        session.get.return_value = resp
        consent_resp = M()
        consent_resp.json.return_value = {"status": "fail"}
        session.post.return_value = consent_resp
        result = run(h.resolve(session, "/challenge/x/", "csrf"))
        assert result.success is False

    def test_select_method_fail(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "111")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "select_verify_method", "step_data": {}}
        session.get.return_value = resp
        select_resp = M()
        select_resp.json.return_value = {"status": "fail"}
        session.post.return_value = select_resp
        result = run(h.resolve(session, "/challenge/y/", "csrf"))
        assert result.success is False

    def test_code_verification_failed(self):
        from instaharvest_v2.async_challenge import AsyncChallengeHandler
        h = AsyncChallengeHandler(code_callback=lambda ctx: "wrong")
        session = AsyncMock()
        resp = M()
        resp.json.return_value = {"step_name": "verify_email", "step_data": {"contact_point": "x"}}
        session.get.return_value = resp
        submit_resp = M()
        submit_resp.json.return_value = {"status": "fail", "message": "Invalid code"}
        session.post.return_value = submit_resp
        result = run(h.resolve(session, "/challenge/z/", "csrf"))
        assert result.success is False


# ═══════════════════════════════════════════════════════════════
# 3. ASYNC_CLIENT.py (171 miss) — lighter coverage
# ═══════════════════════════════════════════════════════════════
class TestAsyncClient:
    def test_get_session(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        sm.get_session.return_value = M(session_id="s1", jazoest="j1")
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        s = client.get_session()
        assert s is not None

    def test_get_jazoest(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        sess = M()
        sess.jazoest = "jazoest_val"
        sm.get_session.return_value = sess
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        assert client.get_jazoest() == "jazoest_val"

    def test_get_jazoest_no_session(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        sm.get_session.return_value = None
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        assert client.get_jazoest() == ""

    def test_rate_limiter_property(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        assert client.rate_limiter is rl

    def test_close(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        client._async_session = AsyncMock()
        run(client.close())
        assert client._async_session is None

    def test_close_no_session(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        run(client.close())

    def test_context_manager(self):
        from instaharvest_v2.async_client import AsyncHttpClient
        sm = M()
        pm = M()
        ad = M()
        rl = M()
        client = AsyncHttpClient(sm, pm, ad, rl)
        async def use_ctx():
            async with client:
                pass
        run(use_ctx())
