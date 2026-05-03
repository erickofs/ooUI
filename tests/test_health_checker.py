"""Tests for HealthChecker — liveness polling without real HTTP."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from gui.workers.health_checker import HealthChecker


class TestHealthChecker:
    """Tests for the health-check worker thread."""

    def test_ping_returns_true_on_200(self):
        """check_once returns True when the server responds 200."""
        with patch("gui.workers.health_checker.urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            checker = HealthChecker(url="http://127.0.0.1:11434/")
            assert checker.check_once() is True

    def test_ping_returns_false_on_connection_error(self):
        """check_once returns False when connection is refused."""
        with patch(
            "gui.workers.health_checker.urllib.request.urlopen",
            side_effect=ConnectionRefusedError("refused"),
        ):
            checker = HealthChecker(url="http://127.0.0.1:11434/")
            assert checker.check_once() is False

    def test_ping_returns_false_on_timeout(self):
        """check_once returns False on network timeout."""
        with patch(
            "gui.workers.health_checker.urllib.request.urlopen",
            side_effect=TimeoutError("timeout"),
        ):
            checker = HealthChecker(url="http://127.0.0.1:11434/")
            assert checker.check_once() is False

    def test_url_property(self):
        """URL can be read and written."""
        checker = HealthChecker(url="http://localhost:1234/")
        assert checker.url == "http://localhost:1234/"
        checker.url = "http://127.0.0.1:5678/"
        assert checker.url == "http://127.0.0.1:5678/"
