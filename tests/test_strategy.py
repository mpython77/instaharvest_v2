"""
test_strategy.py — Strategy Configuration Tests
=================================================
Strategy chain parsing, defaults, enum validation.
"""
import pytest
from instaharvest_v2.strategy import (
    ProfileStrategy, PostsStrategy,
    DEFAULT_PROFILE_STRATEGIES, DEFAULT_POSTS_STRATEGIES,
    parse_profile_strategies, parse_posts_strategies,
)


class TestProfileStrategy:
    def test_enum_values(self):
        assert ProfileStrategy.WEB_API.value == "web_api"
        assert ProfileStrategy.GRAPHQL.value == "graphql"
        assert ProfileStrategy.HTML_PARSE.value == "html_parse"

    def test_defaults(self):
        assert len(DEFAULT_PROFILE_STRATEGIES) >= 2
        assert DEFAULT_PROFILE_STRATEGIES[0] == ProfileStrategy.WEB_API

    def test_parse_none(self):
        result = parse_profile_strategies(None)
        assert result == DEFAULT_PROFILE_STRATEGIES

    def test_parse_list_of_enums(self):
        result = parse_profile_strategies([ProfileStrategy.HTML_PARSE, ProfileStrategy.GRAPHQL])
        assert result == [ProfileStrategy.HTML_PARSE, ProfileStrategy.GRAPHQL]

    def test_parse_list_of_strings(self):
        result = parse_profile_strategies(["html_parse", "web_api"])
        assert result == [ProfileStrategy.HTML_PARSE, ProfileStrategy.WEB_API]


class TestPostsStrategy:
    def test_enum_values(self):
        assert PostsStrategy.WEB_API.value == "web_api"
        assert PostsStrategy.HTML_PARSE.value == "html_parse"

    def test_defaults(self):
        assert len(DEFAULT_POSTS_STRATEGIES) >= 2

    def test_parse_none(self):
        result = parse_posts_strategies(None)
        assert result == DEFAULT_POSTS_STRATEGIES

    def test_parse_list_of_enums(self):
        result = parse_posts_strategies([PostsStrategy.WEB_API])
        assert result == [PostsStrategy.WEB_API]

    def test_parse_list_of_strings(self):
        result = parse_posts_strategies(["web_api", "html_parse"])
        assert result == [PostsStrategy.WEB_API, PostsStrategy.HTML_PARSE]
