"""
test_export_deep.py — Deep ExportAPI Method Body Coverage
===========================================================
ExportFilter.matches() all branches, ExportAPI._export_user_list,
_user_to_row, _write_user_list, followers_to_csv, post_likers,
post_commenters, to_json — full method body execution via mock chain.
~250 miss lines targeted × 2 (sync + async share structure).
"""
import os
import json
import pytest
import tempfile
from unittest.mock import MagicMock

M = MagicMock


# ═══════════════════════════════════════════════════════════
# ExportFilter — all branches
# ═══════════════════════════════════════════════════════════
class TestExportFilter:
    def test_defaults(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter()
        assert ef.min_followers == 0
        assert ef.bio_keywords == []

    def test_matches_pass(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter()
        assert ef.matches({"follower_count": 100, "media_count": 5}) is True

    def test_min_followers(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(min_followers=1000)
        assert ef.matches({"follower_count": 50}) is False

    def test_max_followers(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(max_followers=100)
        assert ef.matches({"follower_count": 500}) is False

    def test_min_following(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(min_following=100)
        assert ef.matches({"following_count": 50}) is False

    def test_max_following(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(max_following=100)
        assert ef.matches({"following_count": 500}) is False

    def test_min_posts(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(min_posts=10)
        assert ef.matches({"media_count": 2}) is False

    def test_is_private(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(is_private=False)
        assert ef.matches({"is_private": True}) is False

    def test_is_verified(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(is_verified=True)
        assert ef.matches({"is_verified": False}) is False

    def test_is_business(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(is_business=True)
        assert ef.matches({"is_business_account": False}) is False

    def test_has_bio_true(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(has_bio=True)
        assert ef.matches({"biography": ""}) is False
        assert ef.matches({"biography": "real bio"}) is True

    def test_has_bio_false(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(has_bio=False)
        assert ef.matches({"biography": "has bio"}) is False
        assert ef.matches({"biography": ""}) is True

    def test_has_profile_pic(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(has_profile_pic=True)
        assert ef.matches({"profile_pic_url": ""}) is False
        assert ef.matches({"profile_pic_url": "default_pic.jpg"}) is False
        assert ef.matches({"profile_pic_url": "https://real.jpg"}) is True

    def test_bio_keywords(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(bio_keywords=["fashion", "model"])
        assert ef.matches({"biography": "I love fashion"}) is True
        assert ef.matches({"biography": "engineer"}) is False

    def test_exclude_keywords(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(exclude_keywords=["spam", "bot"])
        assert ef.matches({"biography": "real bot account"}) is False

    def test_custom_filter(self):
        from instaharvest_v2.api.export import ExportFilter
        ef = ExportFilter(custom_filter=lambda u: u.get("follower_count", 0) > 100)
        assert ef.matches({"follower_count": 50}) is False
        assert ef.matches({"follower_count": 200}) is True


# ═══════════════════════════════════════════════════════════
# ExportAPI — method body deep coverage
# ═══════════════════════════════════════════════════════════
class TestExportAPIDeep:
    def _make(self):
        from instaharvest_v2.api.export import ExportAPI
        return ExportAPI(M(), M(), M(), M(), M())

    def test_user_to_row_dict(self):
        api = self._make()
        row = api._user_to_row({
            "username": "test", "full_name": "Test User", "pk": 123,
            "follower_count": 1000, "following_count": 200, "media_count": 50,
            "is_private": False, "is_verified": True, "is_business_account": True,
            "biography": "test bio", "external_url": "https://site.com",
            "profile_pic_url": "https://pic.jpg", "category_name": "Artist"
        })
        assert row["username"] == "test"
        assert row["user_id"] == 123
        assert row["followers"] == 1000
        assert row["is_verified"] is True
        assert row["category"] == "Artist"

    def test_user_to_row_object(self):
        api = self._make()
        user = M()
        user.username = "objuser"
        user.full_name = "Obj User"
        user.pk = 456
        user.followers = 2000
        user.following = 300
        user.media_count = 100
        user.is_private = True
        user.is_verified = False
        user.is_business_account = True
        user.biography = "bio"
        user.external_url = ""
        user.profile_pic_url = "pic.jpg"
        user.category = "Music"
        user.category_name = ""
        user.user_id = ""
        user.follower_count = 0
        user.following_count = 0
        user.posts_count = 0
        user.is_business = False
        row = api._user_to_row(user)
        assert row["username"] == "objuser"

    def test_user_to_row_str(self):
        api = self._make()
        row = api._user_to_row("just_a_string")
        assert row["username"] == "just_a_string"

    def test_write_user_list(self):
        api = self._make()
        import time
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            result = api._write_user_list(
                [{"username": "u1", "pk": 1}, {"username": "u2", "pk": 2}],
                path, None, "test", time.time()
            )
            assert result["exported"] == 2
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_write_user_list_with_filter(self):
        api = self._make()
        from instaharvest_v2.api.export import ExportFilter
        import time
        ef = ExportFilter(min_followers=100)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            result = api._write_user_list(
                [{"username": "u1", "follower_count": 50}, {"username": "u2", "follower_count": 200}],
                path, ef, "test", time.time()
            )
            assert result["exported"] == 1
            assert result["filtered_out"] == 1
        finally:
            os.unlink(path)

    def test_followers_to_csv(self):
        from instaharvest_v2.api.export import ExportAPI
        mock_users = M()
        mock_users.get_by_username.return_value = {"pk": 123}
        mock_friends = M()
        mock_friends.get_followers.return_value = {
            "users": [{"username": "f1", "pk": 1, "follower_count": 100}],
            "next_max_id": None
        }
        api = ExportAPI(M(), mock_users, mock_friends, M(), M())
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.followers_to_csv("test", path, max_count=1)
            assert result["exported"] == 1
        finally:
            if os.path.exists(path): os.unlink(path)

    def test_post_likers(self):
        from instaharvest_v2.api.export import ExportAPI
        mock_media = M()
        mock_media.get_likers.return_value = {
            "users": [{"username": "liker1", "pk": 1}]
        }
        api = ExportAPI(M(), M(), M(), mock_media, M())
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.post_likers("media_123", path)
            assert result["exported"] == 1
        finally:
            if os.path.exists(path): os.unlink(path)

    def test_post_commenters(self):
        from instaharvest_v2.api.export import ExportAPI
        mock_media = M()
        mock_media.get_all_comments.return_value = [
            {"user": {"username": "c1", "pk": 1}, "text": "nice"},
            {"user": {"username": "c2", "pk": 2}, "text": "great"},
            {"user": {"username": "c1", "pk": 1}, "text": "duplicate"},
        ]
        api = ExportAPI(M(), M(), M(), mock_media, M())
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            result = api.post_commenters("media_123", path)
            assert result["exported"] == 2  # deduped
        finally:
            if os.path.exists(path): os.unlink(path)

    def test_to_json(self):
        from instaharvest_v2.api.export import ExportAPI
        mock_users = M()
        mock_users.get_full_profile.return_value = {"username": "test", "pk": 123}
        mock_client = M()
        mock_client.request.return_value = {"items": [{"id": "post1"}]}
        api = ExportAPI(mock_client, mock_users, M(), M(), M())
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            result = api.to_json("test", path, include_posts=True)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["username"] == "test"
            assert "profile" in data
        finally:
            if os.path.exists(path): os.unlink(path)

    def test_constants(self):
        from instaharvest_v2.api.export import ExportAPI
        assert len(ExportAPI.USER_COLUMNS) > 5
        assert "username" in ExportAPI.USER_COLUMNS
        assert len(ExportAPI.COMMENT_COLUMNS) > 3
