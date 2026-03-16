"""
test_retry.py — RetryConfig Tests
===================================
Pure math: exponential backoff, jitter, ceiling, should_retry.
"""
import pytest
from unittest.mock import patch
from instaharvest_v2.retry import RetryConfig
from instaharvest_v2.exceptions import (
    RateLimitError, NetworkError, ChallengeRequired,
    CheckpointRequired, InstagramError, LoginRequired,
)


class TestCalculateDelay:
    def test_attempt_0(self):
        rc = RetryConfig(jitter=False)
        # 2.0^0 = 1.0
        assert rc.calculate_delay(0) == 1.0

    def test_attempt_1(self):
        rc = RetryConfig(jitter=False)
        # 2.0^1 = 2.0
        assert rc.calculate_delay(1) == 2.0

    def test_attempt_3(self):
        rc = RetryConfig(jitter=False)
        # 2.0^3 = 8.0
        assert rc.calculate_delay(3) == 8.0

    def test_ceiling(self):
        rc = RetryConfig(backoff_max=10.0, jitter=False)
        # 2.0^20 = 1048576, but capped at 10.0
        assert rc.calculate_delay(20) == 10.0

    def test_custom_factor(self):
        rc = RetryConfig(backoff_factor=3.0, jitter=False)
        # 3.0^2 = 9.0
        assert rc.calculate_delay(2) == 9.0

    def test_minimum_delay(self):
        rc = RetryConfig(backoff_factor=0.01, jitter=False)
        # 0.01^0 = 1.0 → no problem; but let's check a case where math is small
        delay = rc.calculate_delay(0)
        assert delay >= 0.1  # min floor

    def test_jitter_with_zero_uniform(self):
        """conftest patches random.uniform to 0.0, so jitter multiplier = 1.0."""
        rc = RetryConfig(jitter=True)
        # With conftest patch: uniform returns 0.0, so multiplier = 1.0 + 0.0 = 1.0
        # base = 4.0 * 1.0 = 4.0
        assert rc.calculate_delay(2) == 4.0

    def test_jitter_with_mock(self):
        rc = RetryConfig(jitter=True)
        with patch("instaharvest_v2.retry.random.uniform", return_value=0.3):
            # base=4, jitter=1.3, result=4*1.3=5.2
            assert rc.calculate_delay(2) == pytest.approx(5.2)
        with patch("instaharvest_v2.retry.random.uniform", return_value=-0.3):
            # base=4, jitter=0.7, result=4*0.7=2.8
            assert rc.calculate_delay(2) == pytest.approx(2.8)


class TestShouldRetry:
    def test_retryable_exceptions(self):
        rc = RetryConfig()
        assert rc.should_retry(RateLimitError("429")) is True
        assert rc.should_retry(NetworkError("timeout")) is True
        assert rc.should_retry(ChallengeRequired("challenge")) is True
        assert rc.should_retry(CheckpointRequired("checkpoint")) is True

    def test_non_retryable_exceptions(self):
        rc = RetryConfig()
        assert rc.should_retry(LoginRequired("login")) is False
        assert rc.should_retry(InstagramError("generic")) is False
        assert rc.should_retry(ValueError("bad")) is False
        assert rc.should_retry(TypeError("type")) is False

    def test_custom_retry_on(self):
        rc = RetryConfig(retry_on={LoginRequired, ValueError})
        assert rc.should_retry(LoginRequired("x")) is True
        assert rc.should_retry(ValueError("y")) is True
        assert rc.should_retry(RateLimitError("z")) is False


class TestDefaults:
    def test_defaults(self):
        rc = RetryConfig()
        assert rc.max_retries == 3
        assert rc.backoff_factor == 2.0
        assert rc.backoff_max == 60.0
        assert rc.jitter is True
        assert RateLimitError in rc.retry_on
        assert NetworkError in rc.retry_on
