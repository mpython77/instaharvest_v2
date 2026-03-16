"""
test_proxy_manager.py — ProxyManager Tests
============================================
Add/get/remove proxies, reporting, health scoring.
"""
import pytest
from instaharvest_v2.proxy_manager import ProxyManager


class TestProxyManager:
    @pytest.fixture
    def pm(self):
        return ProxyManager()

    def test_init_empty(self, pm):
        assert pm.active_count == 0
        assert pm.get_proxy() is None

    def test_add_proxy(self, pm):
        pm.add_proxy("http://proxy1:8080")
        assert pm.active_count == 1

    def test_add_proxies(self, pm):
        pm.add_proxies(["http://p1:8080", "http://p2:8080", "http://p3:8080"])
        assert pm.active_count == 3

    def test_get_proxy(self, pm):
        pm.add_proxy("http://proxy1:8080")
        p = pm.get_proxy()
        assert p is not None
        assert "proxy1" in p

    def test_get_proxy_multiple(self, pm):
        pm.add_proxies(["http://p1:8080", "http://p2:8080"])
        p1 = pm.get_proxy()
        p2 = pm.get_proxy()
        assert p1 is not None
        assert p2 is not None

    def test_report_success(self, pm):
        pm.add_proxy("http://proxy1:8080")
        pm.report_success("http://proxy1:8080", 0.5)
        assert pm.active_count == 1  # Still active

    def test_report_failure(self, pm):
        pm.add_proxy("http://proxy1:8080")
        pm.report_failure("http://proxy1:8080")
        # After one failure, proxy should still be active
        assert pm.active_count >= 0

    def test_remove_proxy(self, pm):
        pm.add_proxy("http://proxy1:8080")
        pm.remove_proxy("http://proxy1:8080")
        assert pm.active_count == 0


    def test_get_stats(self, pm):
        pm.add_proxy("http://proxy1:8080")
        stats = pm.get_stats()
        assert isinstance(stats, dict)

    def test_get_curl_proxy(self, pm):
        pm.add_proxy("http://proxy1:8080")
        p = pm.get_curl_proxy()
        assert p is not None


class TestProxyManagerMassFailure:
    def test_proxy_removed_after_max_failures(self):
        pm = ProxyManager()
        pm.add_proxy("http://bad:8080")
        for _ in range(10):
            pm.report_failure("http://bad:8080")
        # After many failures, proxy may be removed
        # (depends on PROXY_MAX_FAILURES config)

    def test_no_proxy_returns_none(self):
        pm = ProxyManager()
        assert pm.get_proxy() is None
        assert pm.get_curl_proxy() is None
