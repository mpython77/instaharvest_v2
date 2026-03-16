"""
test_parsers.py — Pure Parsing Function Tests
===============================================
No I/O, no mocks — pure input→output verification.
"""
import pytest
from instaharvest_v2.parsers import (
    parse_count,
    parse_meta_tags,
    parse_graphql_user,
    parse_timeline_edges,
    parse_embed_media,
    parse_embed_html,
    parse_mobile_feed_item,
    parse_graphql_docid_media,
)


# ═══════════════════════════════════════════════════════════
# parse_count
# ═══════════════════════════════════════════════════════════
class TestParseCount:
    @pytest.mark.parametrize("text, expected", [
        ("1000", 1000),
        ("1,000", 1000),
        ("1.2K", 1200),
        ("1.2k", 1200),
        ("5K", 5000),
        ("1.5M", 1500000),
        ("2m", 2000000),
        ("0", 0),
        ("", 0),
        ("abc", 0),
        (None, 0),
        ("3,456", 3456),
        ("10.5K", 10500),
    ])
    def test_parse_count(self, text, expected):
        assert parse_count(text) == expected


# ═══════════════════════════════════════════════════════════
# parse_meta_tags
# ═══════════════════════════════════════════════════════════
class TestParseMetaTags:
    def test_full_profile_html(self):
        html = '''
        <title>John Doe (&#064;johndoe) • Instagram photos and videos</title>
        <meta name="description" content="1,234 Followers, 567 Following, 89 Posts - See Instagram photos" />
        <meta property="og:image" content="https://example.com/pic.jpg" />
        '''
        result = parse_meta_tags(html)
        assert result["username"] == "johndoe"
        assert result["full_name"] == "John Doe"
        assert result["followers"] == 1234
        assert result["following"] == 567
        assert result["posts_count"] == 89
        assert result["profile_pic_url"] == "https://example.com/pic.jpg"

    def test_k_m_counts(self):
        html = '''
        <title>Brand (&#064;brand) • Instagram</title>
        <meta content="1.5M Followers, 200 Following, 5K Posts" />
        '''
        result = parse_meta_tags(html)
        assert result["followers"] == 1500000
        assert result["following"] == 200
        assert result["posts_count"] == 5000

    def test_empty_html(self):
        result = parse_meta_tags("")
        assert result == {}

    def test_no_username(self):
        html = "<title>Instagram</title>"
        result = parse_meta_tags(html)
        assert "username" not in result

    def test_bio_from_description(self):
        html = '''
        <title>Jane (&#064;jane) • Instagram</title>
        <meta name="description" content="100 Followers, 50 Following, 10 Posts - Fashion blogger & traveler 🌍" />
        '''
        result = parse_meta_tags(html)
        assert "biography" in result
        assert "Fashion blogger" in result["biography"] or "traveler" in result["biography"]

    def test_og_image(self):
        html = '<meta property="og:image" content="https://cdn.instagram.com/photo.jpg" />'
        result = parse_meta_tags(html)
        assert result.get("profile_pic_url") == "https://cdn.instagram.com/photo.jpg"


# ═══════════════════════════════════════════════════════════
# parse_graphql_user
# ═══════════════════════════════════════════════════════════
class TestParseGraphqlUser:
    @pytest.fixture
    def user_data(self):
        return {
            "id": "12345",
            "username": "testuser",
            "full_name": "Test User",
            "biography": "Hello world",
            "profile_pic_url": "http://pic.jpg",
            "profile_pic_url_hd": "http://pic_hd.jpg",
            "is_private": False,
            "is_verified": True,
            "is_business_account": True,
            "category_name": "Creator",
            "external_url": "https://test.com",
            "edge_followed_by": {"count": 1000},
            "edge_follow": {"count": 500},
            "edge_owner_to_timeline_media": {
                "count": 50,
                "edges": [],
            },
            "bio_links": [{"url": "https://test.com"}],
            "pronouns": ["he/him"],
            "highlight_reel_count": 5,
        }

    def test_all_fields(self, user_data):
        result = parse_graphql_user(user_data)
        assert result["user_id"] == "12345"
        assert result["username"] == "testuser"
        assert result["full_name"] == "Test User"
        assert result["biography"] == "Hello world"
        assert result["is_private"] is False
        assert result["is_verified"] is True
        assert result["is_business"] is True
        assert result["category"] == "Creator"
        assert result["external_url"] == "https://test.com"
        assert result["followers"] == 1000
        assert result["following"] == 500
        assert result["posts_count"] == 50
        assert result["highlight_count"] == 5
        assert result["recent_posts"] == []

    def test_missing_fields(self):
        result = parse_graphql_user({})
        assert result["user_id"] is None
        assert result["username"] is None
        assert result["is_private"] is False
        assert result["followers"] is None


# ═══════════════════════════════════════════════════════════
# parse_timeline_edges
# ═══════════════════════════════════════════════════════════
class TestParseTimelineEdges:
    def test_image_post(self):
        edges = [{"node": {
            "shortcode": "ABC123",
            "__typename": "GraphImage",
            "display_url": "http://img.jpg",
            "thumbnail_src": "http://thumb.jpg",
            "is_video": False,
            "edge_liked_by": {"count": 42},
            "edge_media_to_comment": {"count": 5},
            "edge_media_to_caption": {"edges": [{"node": {"text": "Hello!"}}]},
            "taken_at_timestamp": 1700000000,
            "id": "post1",
        }}]
        result = parse_timeline_edges(edges)
        assert len(result) == 1
        post = result[0]
        assert post["shortcode"] == "ABC123"
        assert post["likes"] == 42
        assert post["comments"] == 5
        assert post["caption"] == "Hello!"
        assert post["is_video"] is False

    def test_no_caption(self):
        edges = [{"node": {
            "edge_media_to_caption": {"edges": []},
            "edge_liked_by": {},
            "edge_media_to_comment": {},
        }}]
        result = parse_timeline_edges(edges)
        assert result[0]["caption"] == ""

    def test_carousel(self):
        edges = [{"node": {
            "edge_media_to_caption": {"edges": []},
            "edge_liked_by": {},
            "edge_media_to_comment": {},
            "edge_sidecar_to_children": {
                "edges": [
                    {"node": {"id": "c1", "display_url": "u1", "is_video": False, "__typename": "GraphImage",
                              "display_resources": [{"src": "r1", "config_width": 640, "config_height": 640}]}},
                    {"node": {"id": "c2", "display_url": "u2", "is_video": True, "__typename": "GraphVideo",
                              "video_url": "v1", "display_resources": []}},
                ],
            },
        }}]
        result = parse_timeline_edges(edges)
        post = result[0]
        assert post["carousel_count"] == 2
        assert post["carousel_media"][0]["pk"] == "c1"
        assert post["carousel_media"][1]["is_video"] is True

    def test_empty(self):
        assert parse_timeline_edges([]) == []


# ═══════════════════════════════════════════════════════════
# parse_mobile_feed_item
# ═══════════════════════════════════════════════════════════
class TestParseMobileFeedItem:
    def test_image(self):
        item = {
            "pk": 123, "id": "123_456", "code": "XYZ",
            "media_type": 1, "like_count": 10, "comment_count": 3,
            "caption": {"text": "Photo caption"},
            "taken_at": 1700000000,
            "image_versions2": {"candidates": [
                {"url": "http://small.jpg", "width": 320, "height": 320},
                {"url": "http://big.jpg", "width": 1080, "height": 1080},
            ]},
        }
        result = parse_mobile_feed_item(item)
        assert result["shortcode"] == "XYZ"
        assert result["media_type"] == "GraphImage"
        assert result["display_url"] == "http://big.jpg"
        assert result["likes"] == 10
        assert result["caption"] == "Photo caption"
        assert result["is_video"] is False

    def test_video(self):
        item = {
            "pk": 200, "media_type": 2,
            "video_versions": [{"url": "http://video.mp4"}],
            "video_duration": 15.5,
            "view_count": 500,
            "image_versions2": {"candidates": [{"url": "http://poster.jpg", "width": 1080, "height": 1080}]},
            "caption": None,
        }
        result = parse_mobile_feed_item(item)
        assert result["media_type"] == "GraphVideo"
        assert result["is_video"] is True
        assert result["video_url"] == "http://video.mp4"
        assert result["video_duration"] == 15.5
        assert result["video_views"] == 500
        assert result["caption"] == ""

    def test_carousel(self):
        item = {
            "pk": 300, "media_type": 8,
            "image_versions2": {"candidates": [{"url": "u", "width": 100, "height": 100}]},
            "carousel_media": [
                {"pk": 301, "media_type": 1,
                 "image_versions2": {"candidates": [{"url": "c1.jpg", "width": 1080, "height": 1080}]}},
                {"pk": 302, "media_type": 2,
                 "video_versions": [{"url": "c2.mp4"}],
                 "image_versions2": {"candidates": [{"url": "c2.jpg", "width": 1080, "height": 1080}]}},
            ],
        }
        result = parse_mobile_feed_item(item)
        assert result["carousel_count"] == 2
        assert result["carousel_media"][0]["is_video"] is False
        assert result["carousel_media"][1]["is_video"] is True
        assert result["carousel_media"][1]["video_url"] == "c2.mp4"

    def test_location(self):
        item = {
            "pk": 400, "media_type": 1,
            "image_versions2": {"candidates": []},
            "location": {"pk": 1, "name": "NYC", "city": "New York", "lat": 40.7, "lng": -74.0},
        }
        result = parse_mobile_feed_item(item)
        assert result["location"]["name"] == "NYC"
        assert result["location"]["lat"] == 40.7

    def test_user_tags(self):
        item = {
            "pk": 500, "media_type": 1,
            "image_versions2": {"candidates": []},
            "usertags": {"in": [
                {"user": {"username": "alice"}},
                {"user": {"username": "bob"}},
                {"user": None},
            ]},
        }
        result = parse_mobile_feed_item(item)
        assert result["tagged_users"] == ["alice", "bob"]


# ═══════════════════════════════════════════════════════════
# parse_embed_media
# ═══════════════════════════════════════════════════════════
class TestParseEmbedMedia:
    def test_full(self):
        media = {
            "id": "e1", "shortcode": "EMB1", "__typename": "GraphImage",
            "is_video": False,
            "edge_media_to_caption": {"edges": [{"node": {"text": "embed caption"}}]},
            "edge_media_preview_like": {"count": 100},
            "edge_media_preview_comment": {"count": 10},
            "taken_at_timestamp": 1700000000,
            "display_url": "http://embed.jpg",
            "display_resources": [{"src": "r1", "config_width": 640, "config_height": 640}],
            "owner": {"username": "owner1", "id": "o1", "is_verified": True, "profile_pic_url": "op.jpg"},
        }
        result = parse_embed_media(media)
        assert result["shortcode"] == "EMB1"
        assert result["caption"] == "embed caption"
        assert result["likes"] == 100
        assert result["owner"]["username"] == "owner1"
        assert len(result["images"]) == 2  # display_url + 1 display_resource

    def test_no_caption(self):
        result = parse_embed_media({"edge_media_to_caption": {"edges": []}})
        assert result["caption"] == ""


# ═══════════════════════════════════════════════════════════
# parse_embed_html
# ═══════════════════════════════════════════════════════════
class TestParseEmbedHtml:
    def test_with_data(self):
        html = '''
        <div class="Caption"><div class="CaptionTextContainer">Beautiful sunset</div></div>
        <a class="UserName">photog</a>
        <img class="EmbeddedMedia" src="http://embed-img.jpg" />
        '''
        result = parse_embed_html(html, "SC1")
        assert result.get("shortcode") == "SC1"
        # This parser depends on exact class formatting

    def test_empty(self):
        result = parse_embed_html("<html></html>", "X")
        assert result == {}


# ═══════════════════════════════════════════════════════════
# parse_graphql_docid_media
# ═══════════════════════════════════════════════════════════
class TestParseGraphqlDocidMedia:
    def test_basic_image(self):
        media = {
            "id": "d1", "shortcode": "DOC1", "__typename": "GraphImage",
            "is_video": False,
            "edge_media_to_caption": {"edges": [{"node": {"text": "docid caption"}}]},
            "edge_media_preview_like": {"count": 50},
            "edge_media_preview_comment": {"count": 8},
            "taken_at_timestamp": 1700000000,
            "display_url": "http://doc.jpg",
            "thumbnail_src": "http://doc_thumb.jpg",
            "dimensions": {"width": 1080, "height": 1080},
            "owner": {"id": "o1", "username": "docowner", "full_name": "Doc",
                     "is_verified": False, "is_private": False,
                     "profile_pic_url": "op.jpg",
                     "edge_followed_by": {"count": 5000},
                     "edge_owner_to_timeline_media": {"count": 100}},
            "display_resources": [{"src": "r1", "config_width": 640, "config_height": 640}],
        }
        result = parse_graphql_docid_media(media)
        assert result["_strategy"] == "graphql_docid"
        assert result["shortcode"] == "DOC1"
        assert result["caption"] == "docid caption"
        assert result["owner"]["username"] == "docowner"
        assert result["owner"]["followers"] == 5000
        assert len(result["display_resources"]) == 1

    def test_with_music(self):
        media = {
            "edge_media_to_caption": {"edges": []},
            "clips_music_attribution_info": {
                "song_name": "Test Song",
                "artist_name": "Artist",
                "audio_id": "a1",
                "uses_original_audio": False,
            },
            "owner": {},
        }
        result = parse_graphql_docid_media(media)
        assert result["audio"]["title"] == "Test Song"
        assert result["audio"]["artist"] == "Artist"

    def test_with_sidecar(self):
        media = {
            "edge_media_to_caption": {"edges": []},
            "owner": {},
            "edge_sidecar_to_children": {
                "edges": [
                    {"node": {"id": "s1", "display_url": "u1", "is_video": False,
                              "__typename": "GraphImage", "display_resources": []}},
                    {"node": {"id": "s2", "display_url": "u2", "is_video": True,
                              "video_url": "v2", "__typename": "GraphVideo", "display_resources": []}},
                ],
            },
        }
        result = parse_graphql_docid_media(media)
        assert result["carousel_count"] == 2
        assert result["carousel_media"][1]["is_video"] is True
