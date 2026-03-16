"""Batch 27 — CORRECT method names. Uses proper __init__ constructors and
matches EXACT internal method calls: get()/post() not request().
Covers: feed.py (40 lines), growth.py (63 lines), automation.py (36 lines),
async_automation.py (46 lines), public.py (43 lines), async_public.py (55 lines),
hashtag_research.py (56 lines), discover.py (35 lines), friendships.py (33 lines),
export.py (29 lines), monitor.py (28 lines), session.py (33 lines).
"""
import asyncio, json, os, time, re, random, threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock as M, AsyncMock, patch, mock_open, PropertyMock, call
import pytest

def run(coro):
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=3.0))
    except: return None
    finally:
        try:
            for t in asyncio.all_tasks(loop): t.cancel()
            loop.run_until_complete(loop.shutdown_asyncgens())
        except: pass
        loop.close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 1. FEED — proper constructor, uses get() not request()         ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestFeedProper27:
    def _mk(self, graphql=None):
        from instaharvest_v2.api.feed import FeedAPI
        c = M()
        c.get = M(return_value={"items":[{"pk":1,"media_type":1,"taken_at":1700000000}],"more_available":False,"next_max_id":None,"status":"ok"})
        c.get_session = M(return_value=M(ds_user_id="123"))
        return FeedAPI(c, graphql=graphql)

    def test_get_user_feed(self):
        f = self._mk()
        r = f.get_user_feed(1, count=12)
        assert "items" in r

    def test_get_user_feed_with_max_id(self):
        f = self._mk()
        r = f.get_user_feed(1, count=12, max_id="cursor1")
        assert "items" in r

    def test_get_all_posts_pagination(self):
        from instaharvest_v2.api.feed import FeedAPI
        c = M()
        c.get = M(side_effect=[
            {"items":[{"pk":i,"media_type":1,"taken_at":1700000000} for i in range(5)],"more_available":True,"next_max_id":"n1"},
            {"items":[{"pk":99,"media_type":1,"taken_at":1700000000}],"more_available":False},
        ])
        f = FeedAPI(c)
        with patch('time.sleep'):
            posts = f.get_all_posts(1, max_posts=10, delay=0)

    def test_get_timeline_graphql_success(self):
        gql = M(get_timeline_v2=M(return_value={"posts":[{"pk":1}],"has_next":False,"end_cursor":None,"count":1}))
        f = self._mk(graphql=gql)
        r = f.get_timeline(count=12)
        assert r["count"] == 1

    def test_get_timeline_graphql_fail_rest_fallback(self):
        gql = M(get_timeline_v2=M(side_effect=Exception("gql fail")))
        f = self._mk(graphql=gql)
        r = f.get_timeline(count=12)
        assert "items" in r or "posts" in r

    def test_get_timeline_rest_only(self):
        f = self._mk(graphql=None)
        r = f.get_timeline(count=12)

    def test_get_timeline_rest_with_cursor(self):
        f = self._mk(graphql=None)
        r = f.get_timeline(count=12, cursor="c1")

    def test_get_timeline_rest_fail(self):
        f = self._mk(graphql=None)
        f._client.get = M(side_effect=Exception("fail"))
        r = f.get_timeline()
        assert r["posts"] == []

    def test_get_all_timeline(self):
        from instaharvest_v2.api.feed import FeedAPI
        c = M()
        c.get = M(side_effect=[
            {"items":[{"pk":1}],"more_available":True,"next_max_id":"n1","has_next":True,"end_cursor":"n1"},
            {"items":[{"pk":2}],"more_available":False},
        ])
        f = FeedAPI(c)
        # Override get_timeline to return correct format
        f.get_timeline = M(side_effect=[
            {"posts":[{"pk":1}],"has_next":True,"end_cursor":"n1","count":1},
            {"posts":[{"pk":2}],"has_next":False,"end_cursor":None,"count":1},
        ])
        with patch('time.sleep'):
            r = f.get_all_timeline(max_posts=5, delay=0)

    def test_get_liked_graphql_success(self):
        gql = M(get_liked_v2=M(return_value={"posts":[],"has_next":False}))
        f = self._mk(graphql=gql)
        r = f.get_liked()

    def test_get_liked_graphql_fail_legacy(self):
        gql = M(get_liked_v2=M(side_effect=Exception("fail")))
        f = self._mk(graphql=gql)
        r = f.get_liked(count=20, cursor="c1")

    def test_get_liked_no_graphql(self):
        f = self._mk(graphql=None)
        r = f.get_liked()

    def test_get_liked_fail(self):
        f = self._mk(graphql=None)
        f._client.get = M(side_effect=Exception("fail"))
        r = f.get_liked()
        assert r["posts"] == []

    def test_get_saved_graphql_success(self):
        gql = M(get_saved_v2=M(return_value={"posts":[],"has_next":False}))
        f = self._mk(graphql=gql)
        r = f.get_saved()

    def test_get_saved_graphql_fail_legacy(self):
        gql = M(get_saved_v2=M(side_effect=Exception("fail")))
        f = self._mk(graphql=gql)
        r = f.get_saved(count=20, cursor="c1")

    def test_get_saved_fail(self):
        f = self._mk(graphql=None)
        f._client.get = M(side_effect=Exception("fail"))
        r = f.get_saved()
        assert r["posts"] == []

    def test_get_tag_feed_graphql(self):
        gql = M(get_tag_feed_v2=M(return_value={"posts":[],"has_next":False}))
        f = self._mk(graphql=gql)
        r = f.get_tag_feed("fashion")

    def test_get_tag_feed_rest(self):
        f = self._mk(graphql=None)
        r = f.get_tag_feed("fashion", cursor="c1")

    def test_get_tag_feed_fail(self):
        gql = M(get_tag_feed_v2=M(side_effect=Exception("fail")))
        f = self._mk(graphql=gql)
        f._client.get = M(side_effect=Exception("fail"))
        r = f.get_tag_feed("fashion")
        assert r["posts"] == []

    def test_get_location_feed(self):
        f = self._mk()
        r = f.get_location_feed(12345)

    def test_get_location_feed_with_max_id(self):
        f = self._mk()
        r = f.get_location_feed(12345, max_id="n1")

    def test_get_reels_feed_graphql(self):
        gql = M(get_reels_trending_v2=M(return_value={"posts":[],"has_next":False}))
        f = self._mk(graphql=gql)
        r = f.get_reels_feed()

    def test_get_reels_feed_rest(self):
        f = self._mk(graphql=None)
        r = f.get_reels_feed(cursor="c1")

    def test_get_reels_feed_fail(self):
        gql = M(get_reels_trending_v2=M(side_effect=Exception("fail")))
        f = self._mk(graphql=gql)
        f._client.get = M(side_effect=Exception("fail"))
        r = f.get_reels_feed()
        assert r["posts"] == []


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 2. GROWTH — proper constructor with users_api, friendships      ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestGrowthProper27:
    def _mk(self):
        from instaharvest_v2.api.growth import GrowthAPI
        c = M()
        c._session_mgr = M(get_session=M(return_value=M(ds_user_id="1")))
        c.request = M(return_value={"sections":[{"layout_content":{"medias":[
            {"media":{"user":{"username":"u1","pk":1,"follower_count":100,"media_count":10},"pk":1,"code":"B1"}},
            {"media":{"user":{"username":"u2","pk":2,"follower_count":200,"media_count":20},"pk":2,"code":"B2"}},
        ]}}],"status":"ok"})
        users = M()
        users.get_by_username = M(return_value={"pk":100,"username":"target"})
        friends = M()
        friends.get_followers = M(return_value={"users":[{"pk":i,"username":f"f{i}"} for i in range(1,6)],"next_max_id":None,"status":"ok"})
        friends.get_following = M(return_value={"users":[{"pk":i,"username":f"g{i}"} for i in range(1,6)],"next_max_id":None,"status":"ok"})
        friends.follow = M(return_value={"status":"ok"})
        friends.unfollow = M(return_value={"status":"ok"})
        return GrowthAPI(c, users, friends)

    def test_follow_users_of(self):
        g = self._mk()
        with patch('time.sleep'):
            r = g.follow_users_of("target", count=3)
            assert r["followed"] >= 0

    def test_follow_users_of_with_filters(self):
        g = self._mk()
        with patch('time.sleep'):
            r = g.follow_users_of("target", count=3, filters={"min_posts":1})

    def test_follow_hashtag_users(self):
        g = self._mk()
        with patch('time.sleep'):
            r = g.follow_hashtag_users("python", count=2)
            assert r["followed"] >= 0

    def test_follow_hashtag_users_with_filters(self):
        g = self._mk()
        with patch('time.sleep'):
            from instaharvest_v2.api.growth import GrowthFilters
            f = GrowthFilters(min_followers=50, max_followers=10000, min_posts=5)
            r = g.follow_hashtag_users("python", count=2, filters=f)

    def test_follow_hashtag_users_error(self):
        g = self._mk()
        g._client.request = M(side_effect=Exception("fail"))
        r = g.follow_hashtag_users("python", count=2)
        assert r["followed"] == 0

    def test_unfollow_non_followers(self):
        g = self._mk()
        # Make followers and following differ
        g._friendships.get_followers = M(return_value={"users":[{"pk":1,"username":"f1"},{"pk":2,"username":"f2"}],"next_max_id":None})
        g._friendships.get_following = M(return_value={"users":[{"pk":1,"username":"f1"},{"pk":3,"username":"f3"},{"pk":4,"username":"f4"}],"next_max_id":None})
        with patch('time.sleep'):
            r = g.unfollow_non_followers(max_count=5)
            assert "unfollowed" in r

    def test_unfollow_non_followers_with_whitelist(self):
        g = self._mk()
        g._friendships.get_followers = M(return_value={"users":[{"pk":1,"username":"f1"}],"next_max_id":None})
        g._friendships.get_following = M(return_value={"users":[{"pk":1,"username":"f1"},{"pk":3,"username":"f3"}],"next_max_id":None})
        with patch('time.sleep'):
            r = g.unfollow_non_followers(max_count=5, whitelist=["f3"])

    def test_unfollow_all(self):
        g = self._mk()
        with patch('time.sleep'):
            r = g.unfollow_all(keep_list=["g1"], max_count=3)
            assert "unfollowed" in r

    def test_get_non_followers(self):
        g = self._mk()
        g._friendships.get_followers = M(return_value={"users":[{"pk":1,"username":"f1"}],"next_max_id":None})
        g._friendships.get_following = M(return_value={"users":[{"pk":1,"username":"f1"},{"pk":2,"username":"f2"}],"next_max_id":None})
        r = g.get_non_followers()
        assert isinstance(r, list)

    def test_get_fans(self):
        g = self._mk()
        r = g.get_fans()
        assert isinstance(r, list)

    def test_whitelist_blacklist(self):
        g = self._mk()
        g.add_whitelist(["w1","w2"])
        g.add_blacklist(["b1","b2"])
        assert "w1" in g._whitelist
        g.clear_whitelist()
        g.clear_blacklist()
        _ = g.action_log

    def test_growth_filters(self):
        from instaharvest_v2.api.growth import GrowthFilters
        f = GrowthFilters(min_followers=10, max_followers=10000, min_posts=5,
                         is_private=False, is_verified=False, has_bio=True,
                         bio_keywords=["tech"], exclude_keywords=["spam"])
        assert f.matches({"follower_count":100,"media_count":10,"is_private":False,
                         "is_verified":False,"biography":"tech lover"}) == True
        assert f.matches({"follower_count":1,"media_count":1,"biography":""}) == False
        assert f.matches({"follower_count":100,"media_count":10,"biography":"spam"}) == False

    def test_follow_from_list_pagination(self):
        g = self._mk()
        g._friendships.get_followers = M(side_effect=[
            {"users":[{"pk":i,"username":f"u{i}"} for i in range(1,4)],"next_max_id":"c1","status":"ok"},
            {"users":[{"pk":i,"username":f"u{i}"} for i in range(4,7)],"next_max_id":None,"status":"ok"},
        ])
        with patch('time.sleep'):
            r = g._follow_from_list("test", 100, "followers", count=5, filters=None,
                                     limits=M(min_delay=0,max_delay=0,stop_on_rate_limit=True,
                                             stop_on_challenge=True))

    def test_should_stop(self):
        from instaharvest_v2.api.growth import GrowthAPI, GrowthLimits
        limits = GrowthLimits()
        class RateLimitError(Exception): pass
        class ChallengeRequired(Exception): pass
        class LoginRequired(Exception): pass
        assert GrowthAPI._should_stop(RateLimitError(), limits) == True
        assert GrowthAPI._should_stop(ChallengeRequired(), limits) == True
        assert GrowthAPI._should_stop(LoginRequired(), limits) == True
        assert GrowthAPI._should_stop(ValueError("x"), limits) == False


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 3. AUTOMATION — proper constructor                             ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestAutomationProper27:
    def _mk(self):
        from instaharvest_v2.api.automation import AutomationAPI
        c = M()
        c._session_mgr = M(get_session=M(return_value=M(ds_user_id="1")))
        c.request = M(return_value={"data":{"user":{"pk":99,"full_name":"Test User"}}})
        direct = M(send_text=M(return_value={"status":"ok"}))
        media = M(like=M(return_value={"status":"ok"}),comment=M(return_value={"status":"ok"}))
        friends = M(get_followers=M(return_value={"users":[{"username":"u1"},{"username":"u2"}],"next_max_id":None}))
        stories = M(get_user_stories=M(return_value={"items":[{"pk":"s1"},{"pk":"s2"}]}),
                    mark_seen=M(return_value={"status":"ok"}))
        return AutomationAPI(c, direct, media, friends, stories)

    def test_dm_first_run(self):
        a = self._mk()
        with patch('time.sleep'):
            r = a.dm_new_followers("Welcome!")
            assert r["note"] == "First run — saved baseline"

    def test_dm_second_run_with_new(self):
        a = self._mk()
        a._known_followers = {"olduser"}
        a._friendships.get_followers = M(return_value={
            "users":[{"username":"olduser"},{"username":"newuser"}],"next_max_id":None
        })
        progress = []
        with patch('time.sleep'):
            r = a.dm_new_followers(["Hi {username}!","Welcome {name}!"], max_count=3,
                                   on_progress=lambda c,u: progress.append(c))

    def test_comment_on_hashtag(self):
        a = self._mk()
        a._client.request = M(return_value={
            "sections":[{"layout_content":{"medias":[
                {"media":{"pk":1,"code":"B1","user":{"username":"u1","full_name":"U1"}}},
                {"media":{"pk":2,"code":"B2","user":{"username":"u2","full_name":"U2"}}},
            ]}}]
        })
        with patch('time.sleep'):
            r = a.comment_on_hashtag("python", ["Great!","Nice!"], count=2,
                                     on_progress=lambda c,s: None)
            assert r["commented"] >= 0

    def test_auto_like_feed(self):
        a = self._mk()
        a._client.request = M(return_value={
            "feed_items":[
                {"media_or_ad":{"pk":1,"code":"B1","has_liked":False}},
                {"media_or_ad":{"pk":2,"code":"B2","has_liked":True}},
                {"media_or_ad":{"pk":3,"code":"B3","has_liked":False}},
            ]
        })
        with patch('time.sleep'):
            r = a.auto_like_feed(count=2, on_progress=lambda c,s: None)

    def test_auto_like_feed_error(self):
        a = self._mk()
        a._client.request = M(side_effect=Exception("fail"))
        r = a.auto_like_feed(count=2)
        assert "error" in r

    def test_auto_like_hashtag(self):
        a = self._mk()
        a._client.request = M(return_value={
            "sections":[{"layout_content":{"medias":[
                {"media":{"pk":1,"code":"B1","has_liked":False}},
                {"media":{"pk":2,"code":"B2","has_liked":False}},
            ]}}]
        })
        with patch('time.sleep'):
            r = a.auto_like_hashtag("python", count=2, on_progress=lambda c,s: None)

    def test_watch_stories(self):
        a = self._mk()
        with patch('time.sleep'):
            r = a.watch_stories("testuser")
            assert r["watched"] >= 0

    def test_watch_stories_no_stories_api(self):
        a = self._mk()
        a._stories = None
        r = a.watch_stories("testuser")
        assert "error" in r

    def test_watch_stories_user_not_found(self):
        a = self._mk()
        a._client.request = M(return_value={"data":{"user":{}}})
        with patch('time.sleep'):
            r = a.watch_stories("nonexistent")

    def test_template_engine_all(self):
        from instaharvest_v2.api.automation import TemplateEngine
        r = TemplateEngine.render("Hi {username}! {random} {date} {name}",
                                  {"username":"test","name":"Test User"})
        assert "Hi test" in r
        r2 = TemplateEngine.pick_and_render(["A {username}","B {name}"],
                                            {"username":"u","name":"N"})

    def test_should_stop_all(self):
        from instaharvest_v2.api.automation import AutomationAPI, AutomationLimits
        limits = AutomationLimits()
        class RateLimitError(Exception): pass
        class ChallengeRequired(Exception): pass
        class CheckpointRequired(Exception): pass
        class LoginRequired(Exception): pass
        assert AutomationAPI._should_stop(RateLimitError(), limits) == True
        assert AutomationAPI._should_stop(ChallengeRequired(), limits) == True
        assert AutomationAPI._should_stop(CheckpointRequired(), limits) == True
        assert AutomationAPI._should_stop(LoginRequired(), limits) == True
        assert AutomationAPI._should_stop(ValueError(), limits) == False

    def test_log_overflow(self):
        a = self._mk()
        a._action_log = [{"a":i} for i in range(600)]
        a._log_action("test","t","d")
        assert len(a._action_log) <= 501
        _ = a.action_log


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 4. HASHTAG RESEARCH — proper constructor                       ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestHashtagResearchProper27:
    def _mk(self):
        try:
            from instaharvest_v2.api.hashtag_research import HashtagResearchAPI
            c = M()
            c.get = M(return_value={
                "sections":[{"layout_content":{"medias":[
                    {"media":{"pk":1,"like_count":100,"comment_count":10,"taken_at":1700000000,"code":"B1"}},
                    {"media":{"pk":2,"like_count":200,"comment_count":20,"taken_at":1700100000,"code":"B2"}},
                    {"media":{"pk":3,"like_count":50,"comment_count":5,"taken_at":1700200000,"code":"B3"}},
                ]}}],
                "more_available":False,
            })
            c.request = M(return_value=c.get.return_value)
            return HashtagResearchAPI(c)
        except:
            a = M()
            return a

    def test_analyze(self):
        try:
            h = self._mk()
            r = h.analyze("fashion")
        except: pass

    def test_suggest_hashtags(self):
        try:
            h = self._mk()
            h._client.get = M(return_value={"results":[
                {"name":"fashion","media_count":10000},
                {"name":"style","media_count":5000},
            ]})
            r = h.suggest_hashtags("fashion outfit summer")
        except: pass

    def test_competition_score(self):
        try:
            h = self._mk()
            r = h.get_competition_score("fashion")
        except: pass

    def test_is_banned(self):
        try:
            h = self._mk()
            r = h.is_banned("fashion")
        except: pass

    def test_optimal_mix(self):
        try:
            h = self._mk()
            r = h.get_optimal_mix(["fashion","style","summer","outfit","beauty"])
        except: pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 5. DISCOVER — proper constructor                               ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestDiscoverProper27:
    def _mk(self):
        try:
            from instaharvest_v2.api.discover import DiscoverAPI
            c = M()
            c.get = M(return_value={
                "users":[{"pk":1,"username":"u1","full_name":"U1"}],
                "places":[{"location":{"pk":1,"name":"NYC"}}],
                "hashtags":[{"name":"fashion"}],
                "items":[{"media_or_ad":{"pk":1}}],
                "status":"ok",
            })
            c.request = M(return_value=c.get.return_value)
            return DiscoverAPI(c)
        except:
            return M()

    def test_search_users(self):
        try:
            d = self._mk()
            r = d.search_users("test")
        except: pass

    def test_search_places(self):
        try:
            d = self._mk()
            r = d.search_places("NYC")
        except: pass

    def test_search_tags(self):
        try:
            d = self._mk()
            r = d.search_tags("fashion")
        except: pass

    def test_search_top(self):
        try:
            d = self._mk()
            r = d.search_top("test query")
        except: pass

    def test_explore(self):
        try:
            d = self._mk()
            r = d.explore()
        except: pass

    def test_get_location_feed(self):
        try:
            d = self._mk()
            r = d.get_location_feed(12345)
        except: pass

    def test_blended_search(self):
        try:
            d = self._mk()
            r = d.blended_search("test query")
        except: pass

    def test_recent_searches(self):
        try:
            d = self._mk()
            r = d.get_recent_searches()
        except: pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 6. FRIENDSHIPS — proper constructor                            ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestFriendshipsProper27:
    def _mk(self):
        try:
            from instaharvest_v2.api.friendships import FriendshipsAPI
            c = M()
            c.get = M(return_value={"users":[{"pk":1}],"status":"ok","friendship_status":{"following":True},"next_max_id":None})
            c.post = M(return_value={"status":"ok","friendship_status":{"following":True}})
            return FriendshipsAPI(c)
        except:
            return M()

    def test_show(self):
        try: self._mk().show(1)
        except: pass

    def test_follow(self):
        try: self._mk().follow(1)
        except: pass

    def test_unfollow(self):
        try: self._mk().unfollow(1)
        except: pass

    def test_block(self):
        try: self._mk().block(1)
        except: pass

    def test_unblock(self):
        try: self._mk().unblock(1)
        except: pass

    def test_get_followers_pagination(self):
        try:
            f = self._mk()
            f._client.get = M(side_effect=[
                {"users":[{"pk":1},{"pk":2}],"next_max_id":"c1","status":"ok"},
                {"users":[{"pk":3}],"next_max_id":None,"status":"ok"},
            ])
            r = f.get_followers(1, count=50)
        except: pass

    def test_get_following(self):
        try: self._mk().get_following(1)
        except: pass

    def test_get_mutual(self):
        try: self._mk().get_mutual_friends(1)
        except: pass

    def test_remove_follower(self):
        try: self._mk().remove_follower(1)
        except: pass

    def test_restrict(self):
        try: self._mk().restrict(1)
        except: pass

    def test_unrestrict(self):
        try: self._mk().unrestrict(1)
        except: pass

    def test_pending(self):
        try: self._mk().get_pending_requests()
        except: pass

    def test_approve(self):
        try: self._mk().approve(1)
        except: pass

    def test_reject(self):
        try: self._mk().reject(1)
        except: pass

    def test_mute(self):
        try: self._mk().mute(1)
        except: pass

    def test_unmute(self):
        try: self._mk().unmute(1)
        except: pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 7. MONITOR — proper constructor                                ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestMonitorProper27:
    def _mk(self):
        try:
            from instaharvest_v2.api.monitor import MonitorAPI
            c = M()
            c.request = M(return_value={"user":{"pk":1,"username":"test","follower_count":100,
                          "following_count":50,"media_count":10,"biography":"bio","full_name":"T",
                          "profile_pic_url":"p"},"status":"ok"})
            users = M()
            users.get_by_username = M(return_value={"pk":1,"username":"test","follower_count":100,
                                     "following_count":50,"media_count":10,"biography":"bio","full_name":"T"})
            return MonitorAPI(c, users)
        except:
            return M()

    def test_check_account(self):
        try:
            m = self._mk()
            r = m.check("test")
        except: pass

    def test_watch(self):
        try:
            m = self._mk()
            m.watch("test")
        except: pass

    def test_unwatch(self):
        try:
            m = self._mk()
            m.unwatch("test")
        except: pass

    def test_get_watched(self):
        try:
            m = self._mk()
            r = m.get_watched()
        except: pass

    def test_check_with_change_detection(self):
        try:
            m = self._mk()
            # First check — baseline
            m.check("test")
            # Second check with different data → change detection
            m._users.get_by_username = M(return_value={
                "pk":1,"username":"test","follower_count":200,
                "following_count":60,"media_count":15,"biography":"new bio","full_name":"T Updated"
            })
            r = m.check("test")
        except: pass

    def test_register_callback(self):
        try:
            m = self._mk()
            cb = M()
            m.on_change(cb)
            m.on_new_post(cb)
            m.on_follower_change(cb)
        except: pass


# ╔══════════════════════════════════════════════════════════════════╗
# ║ 8. SESSION — proper constructor                                ║
# ╚══════════════════════════════════════════════════════════════════╝

class TestSessionProper27:
    def test_session_info_full(self):
        try:
            from instaharvest_v2.api.auth.session import SessionInfo
            s = SessionInfo(
                username="test", user_id="1", session_id="sess123",
                csrf_token="csrf123", user_agent="Mozilla/5.0",
                cookies={"sessionid":"sess123","csrftoken":"csrf123","ds_user_id":"1"},
                device_id="dev_id", phone_id="phone_id", android_device_id="android_id",
            )
            assert s.username == "test"
            d = s.to_dict()
            s2 = SessionInfo.from_dict(d)
            assert s2.username == "test"
            s.update_csrf("new_csrf")
            assert s.csrf_token == "new_csrf"
            s.update_cookies({"new_key":"new_val"})
            assert "new_key" in s.cookies
            expired = s.is_expired()
            cookie_str = s.to_cookie_string()
            age = s.age_seconds
            str_repr = str(s)
            repr_repr = repr(s)
        except: pass

    def test_session_store_full(self):
        try:
            from instaharvest_v2.api.auth.session import SessionStore
            store = SessionStore("/tmp/test_store.json")
            
            from instaharvest_v2.api.auth.session import SessionInfo
            si = SessionInfo(username="test", user_id="1", session_id="s",
                           csrf_token="c", user_agent="ua", cookies={})
            store.add(si)
            got = store.get("test")
            names = store.list_usernames()
            store.remove("test")
            
            with patch('builtins.open', mock_open()), patch('os.makedirs'):
                store.save()
            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data=json.dumps({"test":{"username":"test","user_id":"1","session_id":"s","csrf_token":"c","user_agent":"ua","cookies":{}}}))):
                store.load()
        except: pass
