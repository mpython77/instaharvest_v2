"""
test_exceptions.py — Exception Hierarchy Tests
================================================
Verifies InstagramError base class and all specialized exceptions.
"""
import pytest
from instaharvest_v2.exceptions import (
    InstagramError,
    LoginRequired,
    RateLimitError,
    PrivateAccountError,
    NotFoundError,
    ChallengeRequired,
    CheckpointRequired,
    ConsentRequired,
    NetworkError,
    ProxyError,
    MediaNotFound,
    UserNotFound,
)


class TestInstagramError:
    def test_default_values(self):
        err = InstagramError()
        assert err.message == ""
        assert err.status_code == 0
        assert err.response == {}

    def test_custom_values(self):
        err = InstagramError("bad request", status_code=400, response={"detail": "x"})
        assert err.message == "bad request"
        assert err.status_code == 400
        assert err.response == {"detail": "x"}
        assert str(err) == "bad request"

    def test_is_exception(self):
        assert issubclass(InstagramError, Exception)


class TestSubclasses:
    @pytest.mark.parametrize("cls", [
        LoginRequired, RateLimitError, PrivateAccountError,
        NotFoundError, CheckpointRequired, ConsentRequired,
        NetworkError, ProxyError,
    ])
    def test_inherits_instagram_error(self, cls):
        assert issubclass(cls, InstagramError)
        err = cls("msg", status_code=500)
        assert err.message == "msg"
        assert err.status_code == 500

    def test_media_not_found_inherits_not_found(self):
        assert issubclass(MediaNotFound, NotFoundError)
        assert issubclass(MediaNotFound, InstagramError)

    def test_user_not_found_inherits_not_found(self):
        assert issubclass(UserNotFound, NotFoundError)
        assert issubclass(UserNotFound, InstagramError)


class TestChallengeRequired:
    def test_challenge_url_from_dict(self):
        err = ChallengeRequired(
            "challenge",
            response={"challenge": {"url": "/challenge/123/", "challenge_type": "email"}},
        )
        assert err.challenge_url == "/challenge/123/"
        assert err.challenge_type == "email"

    def test_challenge_url_from_string(self):
        err = ChallengeRequired("challenge", response={"challenge": "/c/456/"})
        assert err.challenge_url == "/c/456/"
        assert err.challenge_type == "unknown"

    def test_challenge_url_empty(self):
        err = ChallengeRequired("challenge", response={})
        assert err.challenge_url == ""
        assert err.challenge_type == "unknown"

    def test_challenge_url_none(self):
        err = ChallengeRequired("challenge", response={"challenge": None})
        assert err.challenge_url == ""

    def test_challenge_type_missing(self):
        err = ChallengeRequired("c", response={"challenge": {"url": "/x/"}})
        assert err.challenge_type == "unknown"
