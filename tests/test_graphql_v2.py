"""
Tests — GraphQL v2 Methods & Discover Chain
==============================================
Unit tests for new GraphQL v2 methods and discover chain functionality.
"""

import json
import unittest
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════
# TEST: DOC_IDS Registry
# ═══════════════════════════════════════════════════════════

class TestDocIDsRegistry(unittest.TestCase):
    """Test that DOC_IDS registry has all required keys."""

    def test_verified_doc_ids_present(self):
        from instaharvest_v2.api.graphql import DOC_IDS
        verified_keys = [
            "profile_posts", "profile_reels", "profile_tagged",
            "profile_hover_card", "profile_highlights", "profile_suggested",
            "feed_timeline", "feed_timeline_pagination",
            "feed_reels_trending", "feed_saved",
            "media_comments", "like_media", "stories_seen",
            "search_null_state",
        ]
        for key in verified_keys:
            self.assertIn(key, DOC_IDS, f"Missing verified doc_id: {key}")
            self.assertTrue(DOC_IDS[key].isdigit(), f"doc_id for {key} should be numeric")

    def test_doc_ids_are_strings(self):
        from instaharvest_v2.api.graphql import DOC_IDS
        for key, value in DOC_IDS.items():
            self.assertIsInstance(value, str, f"{key} should be string")

    def test_no_duplicate_doc_ids(self):
        from instaharvest_v2.api.graphql import DOC_IDS
        values = list(DOC_IDS.values())
        # Some doc_ids might be shared, but most should be unique
        unique = set(values)
        self.assertGreater(len(unique), len(values) * 0.8, "Too many duplicate doc_ids")


# ═══════════════════════════════════════════════════════════
# TEST: GraphQLAPI.get_hover_card
# ═══════════════════════════════════════════════════════════

class TestGetHoverCard(unittest.TestCase):
    """Test get_hover_card method."""

    def setUp(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        self.client = MagicMock()
        self.api = GraphQLAPI(self.client)

    def test_hover_card_parses_response(self):
        """Test that hover card correctly parses API response."""
        self.client.post.return_value = {
            "data": {
                "xdt_api__v1__users__info": {
                    "pk": 48998461622,
                    "username": "sarvish_m",
                    "full_name": "Sarvish",
                    "biography": "Model & Creator",
                    "is_verified": False,
                    "is_private": False,
                    "follower_count": 103969,
                    "following_count": 500,
                    "media_count": 73,
                    "profile_pic_url": "https://example.com/pic.jpg",
                    "friendship_status": {
                        "following": False,
                        "followed_by": False,
                        "blocking": False,
                        "muting": False,
                    },
                    "mutual_followers": {
                        "count": 2,
                        "users": [
                            {"pk": 1, "username": "mutual1", "full_name": "M1", "profile_pic_url": ""},
                        ]
                    },
                }
            }
        }

        result = self.api.get_hover_card("48998461622", "sarvish_m")

        self.assertEqual(result["username"], "sarvish_m")
        self.assertEqual(result["full_name"], "Sarvish")
        self.assertEqual(result["follower_count"], 103969)
        self.assertEqual(result["media_count"], 73)
        self.assertEqual(result["biography"], "Model & Creator")
        self.assertFalse(result["is_following"])
        self.assertEqual(result["mutual_count"], 2)
        self.assertEqual(len(result["mutual_followers"]), 1)

    def test_hover_card_empty_response(self):
        """Test hover card with empty response."""
        self.client.post.return_value = {"data": {}}
        result = self.api.get_hover_card("123", "test")
        self.assertIsNone(result["pk"])
        self.assertEqual(result["username"], "test")


# ═══════════════════════════════════════════════════════════
# TEST: GraphQLAPI.get_suggested_users
# ═══════════════════════════════════════════════════════════

class TestGraphQLGetSuggestedUsers(unittest.TestCase):
    """Test GraphQL get_suggested_users method."""

    def setUp(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        self.client = MagicMock()
        self.api = GraphQLAPI(self.client)

    def test_suggested_users_parses_response(self):
        """Test parsing suggested users from API response."""
        self.client.post.return_value = {
            "data": {
                "xdt_api__v1__discover__chaining": {
                    "users": [
                        {"pk": 1, "username": "user1", "full_name": "User One",
                         "is_verified": True, "is_private": False, "profile_pic_url": "",
                         "follower_count": 50000, "social_context": "Followed by X"},
                        {"pk": 2, "username": "user2", "full_name": "User Two",
                         "is_verified": False, "is_private": False, "profile_pic_url": "",
                         "follower_count": 10000},
                    ]
                }
            }
        }

        result = self.api.get_suggested_users("12345")

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["users"][0]["username"], "user1")
        self.assertTrue(result["users"][0]["is_verified"])
        self.assertEqual(result["users"][1]["follower_count"], 10000)

    def test_suggested_users_empty(self):
        """Test with empty response."""
        self.client.post.return_value = {"data": {}}
        result = self.api.get_suggested_users("12345")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["users"], [])


# ═══════════════════════════════════════════════════════════
# TEST: GraphQLAPI.like_media
# ═══════════════════════════════════════════════════════════

class TestLikeMedia(unittest.TestCase):
    """Test like_media mutation."""

    def setUp(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        self.client = MagicMock()
        self.api = GraphQLAPI(self.client)

    def test_like_success(self):
        """Test successful like."""
        self.client.post.return_value = {
            "data": {
                "xdt_like_media": {"media": {"pk": "123"}}
            }
        }

        result = self.api.like_media("123456789")
        self.assertTrue(result["success"])
        self.assertEqual(result["media_id"], "123456789")

    def test_like_error(self):
        """Test like with exception."""
        self.client.post.side_effect = Exception("Rate limited")

        result = self.api.like_media("123456789")
        self.assertFalse(result["success"])
        self.assertIn("error", result)


# ═══════════════════════════════════════════════════════════
# TEST: GraphQLAPI.get_comments_v2
# ═══════════════════════════════════════════════════════════

class TestGetCommentsV2(unittest.TestCase):
    """Test get_comments_v2 method."""

    def setUp(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        self.client = MagicMock()
        self.api = GraphQLAPI(self.client)

    def test_comments_parses_response(self):
        """Test comment parsing."""
        self.client.post.return_value = {
            "data": {
                "xdt_api__v1__media__media_id__comments__connection": {
                    "edges": [
                        {"node": {
                            "pk": "c1", "text": "Great post!",
                            "created_at": 1700000000,
                            "comment_like_count": 5,
                            "user": {"pk": 1, "username": "commenter1", "full_name": "C1",
                                     "is_verified": False, "profile_pic_url": ""},
                            "child_comment_count": 2,
                            "preview_child_comments": [],
                            "has_liked_comment": False,
                        }},
                        {"node": {
                            "pk": "c2", "text": "Nice!",
                            "created_at": 1700001000,
                            "comment_like_count": 0,
                            "user": {"pk": 2, "username": "commenter2", "full_name": "C2",
                                     "is_verified": True, "profile_pic_url": ""},
                            "child_comment_count": 0,
                            "preview_child_comments": None,
                            "has_liked_comment": True,
                        }},
                    ],
                    "page_info": {"has_next_page": True, "end_cursor": "abc123"},
                }
            }
        }

        result = self.api.get_comments_v2("3843229444966511752", count=10)

        self.assertEqual(result["count"], 2)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["end_cursor"], "abc123")

        c1 = result["comments"][0]
        self.assertEqual(c1["text"], "Great post!")
        self.assertEqual(c1["like_count"], 5)
        self.assertEqual(c1["user"]["username"], "commenter1")
        self.assertTrue(c1["has_replies"])
        self.assertEqual(c1["child_comment_count"], 2)

        c2 = result["comments"][1]
        self.assertTrue(c2["is_liked"])


# ═══════════════════════════════════════════════════════════
# TEST: DiscoverAPI
# ═══════════════════════════════════════════════════════════

class TestDiscoverAPI(unittest.TestCase):
    """Test DiscoverAPI doc_id and methods."""

    def test_doc_id_is_verified(self):
        from instaharvest_v2.api.discover import DISCOVER_CHAINING_DOC_ID
        self.assertEqual(DISCOVER_CHAINING_DOC_ID, "25814188068245954")

    def test_friendly_name_correct(self):
        """Test that get_suggested_users_raw uses correct friendly_name."""
        from instaharvest_v2.api.discover import DiscoverAPI
        client = MagicMock()
        client.post.return_value = {"data": {}}
        api = DiscoverAPI(client)
        api.get_suggested_users_raw("12345")

        call_args = client.post.call_args
        payload = call_args.kwargs.get("data") or call_args[1].get("data")
        self.assertEqual(
            payload["fb_api_req_friendly_name"],
            "PolarisProfileSuggestedUsersWithPreloadableQuery"
        )

    def test_variables_include_module(self):
        """Test that variables include module field."""
        from instaharvest_v2.api.discover import DiscoverAPI
        client = MagicMock()
        client.post.return_value = {"data": {}}
        api = DiscoverAPI(client)
        api.get_suggested_users_raw("12345")

        call_args = client.post.call_args
        payload = call_args.kwargs.get("data") or call_args[1].get("data")
        variables = json.loads(payload["variables"])
        self.assertEqual(variables["module"], "profile")
        self.assertEqual(variables["target_id"], "12345")


# ═══════════════════════════════════════════════════════════
# TEST: DiscoverAPI.chain
# ═══════════════════════════════════════════════════════════

class TestDiscoverChain(unittest.TestCase):
    """Test discover chain method."""

    def setUp(self):
        from instaharvest_v2.api.discover import DiscoverAPI
        from instaharvest_v2.models.user import UserShort
        self.client = MagicMock()
        self.api = DiscoverAPI(self.client)
        self.UserShort = UserShort

    def _make_users(self, prefix, count):
        """Helper to create mock user list."""
        return [
            self.UserShort(
                pk=i + 1000,
                username=f"{prefix}_{i}",
                full_name=f"{prefix} {i}",
                is_verified=False,
                is_private=False,
                profile_pic_url="",
            )
            for i in range(count)
        ]

    @patch("time.sleep")  # Skip delays in tests
    def test_chain_single_layer(self, mock_sleep):
        """Test chain with depth=1 (single layer)."""
        with patch.object(self.api, "get_suggested_users") as mock_suggest:
            mock_suggest.return_value = self._make_users("user", 5)

            result = self.api.chain(
                seed_user_id="12345",
                max_depth=1,
                max_per_layer=3,
                delay=0,
            )

            self.assertEqual(result["total_unique"], 5)
            self.assertEqual(result["seed_id"], "12345")
            self.assertEqual(len(result["users"]), 5)
            # All users should have layer 0 (from seed)
            for u in result["users"]:
                self.assertEqual(u["layer"], 0)

    @patch("time.sleep")
    def test_chain_progress_callback(self, mock_sleep):
        """Test chain progress callback is called."""
        progress_calls = []

        def on_progress(layer, i, total, username, new_count, total_unique):
            progress_calls.append({
                "layer": layer, "i": i, "total": total,
                "username": username, "new_count": new_count,
            })

        with patch.object(self.api, "get_suggested_users") as mock_suggest:
            mock_suggest.return_value = self._make_users("u", 3)

            self.api.chain(
                seed_user_id="12345",
                max_depth=2,
                max_per_layer=2,
                delay=0,
                on_progress=on_progress,
            )

        self.assertGreater(len(progress_calls), 0)

    @patch("time.sleep")
    def test_chain_deduplication(self, mock_sleep):
        """Test that chain deduplicates users across layers."""
        with patch.object(self.api, "get_suggested_users") as mock_suggest:
            # Both layers return the same users
            same_users = self._make_users("same", 3)
            mock_suggest.return_value = same_users

            result = self.api.chain(
                seed_user_id="12345",
                max_depth=2,
                max_per_layer=2,
                delay=0,
            )

            # Should only have 3 unique users despite multiple layers
            self.assertEqual(result["total_unique"], 3)


# ═══════════════════════════════════════════════════════════
# TEST: Timeline v2 parsing
# ═══════════════════════════════════════════════════════════

class TestTimelineV2Parsing(unittest.TestCase):
    """Test timeline connection parsing."""

    def setUp(self):
        from instaharvest_v2.api.graphql import GraphQLAPI
        self.client = MagicMock()
        self.api = GraphQLAPI(self.client)

    def test_parse_timeline_connection(self):
        """Test parsing timeline edges."""
        data = {
            "data": {
                "xdt_api__v1__feed__timeline__connection": {
                    "edges": [
                        {"node": {"media": {
                            "pk": "123", "code": "ABC", "media_type": 1,
                            "like_count": 100, "comment_count": 10,
                            "user": {"pk": 1, "username": "user1"},
                            "caption": {"text": "Test caption"},
                        }}},
                    ],
                    "page_info": {"has_next_page": True, "end_cursor": "cursor123"},
                }
            }
        }

        result = self.api._parse_timeline_connection(
            data, "xdt_api__v1__feed__timeline__connection"
        )

        self.assertEqual(result["count"], 1)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["end_cursor"], "cursor123")
        self.assertEqual(result["posts"][0]["like_count"], 100)
        self.assertEqual(result["posts"][0]["user"]["username"], "user1")

    def test_parse_empty_connection(self):
        """Test parsing empty connection."""
        result = self.api._parse_timeline_connection(
            {"data": {}}, "nonexistent_key"
        )
        self.assertEqual(result["count"], 0)
        self.assertFalse(result["has_next"])


if __name__ == "__main__":
    unittest.main()
