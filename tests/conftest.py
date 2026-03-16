"""
conftest.py — Global Test Fixtures
===================================
Patches blocking calls so tests don't hang.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def _patch_all_blocking():
    """Patch every time.sleep / random delay to prevent hanging tests."""
    with (
        patch("instaharvest_v2.anti_detect.time.sleep"),
        patch("instaharvest_v2.client.time.sleep"),
        patch("time.sleep"),
        patch("instaharvest_v2.anti_detect.random.gauss", return_value=0.0),
        patch("instaharvest_v2.anti_detect.random.uniform", return_value=0.0),
    ):
        yield


@pytest.fixture(autouse=True)
def _patch_monitor_threads():
    """Prevent MonitorAPI from spawning real threads."""
    with (
        patch("instaharvest_v2.api.monitor.MonitorAPI.start", return_value=None),
        patch("instaharvest_v2.api.monitor.MonitorAPI.stop", return_value=None),
    ):
        yield
