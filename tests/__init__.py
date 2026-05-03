"""Shared test fixtures for ooProxy GUI tests."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def fake_ooproxy_dir(tmp_path: Path):
    """Create a temporary .ooproxy directory with a keys file."""
    ooproxy_dir = tmp_path / ".ooproxy"
    ooproxy_dir.mkdir()
    return ooproxy_dir


@pytest.fixture
def fake_keys_file(fake_ooproxy_dir: Path):
    """Create a DPAPI-format keys file (with fake encrypted values)."""
    keys_file = fake_ooproxy_dir / "keys"
    data = {
        "version": "v2-dpapi",
        "url": "https://integrate.api.nvidia.com/v1",
        "entries": {
            "integrate.api.nvidia.com": "FAKE_DPAPI_ENCRYPTED_STRING_001",
        },
        "timestamp": "2026-01-01T00:00:00Z",
    }
    keys_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return keys_file


@pytest.fixture
def mock_qprocess():
    """Return a fully mocked QProcess class."""
    with patch("gui.workers.proxy_process.QProcess") as MockQProcess:
        instance = MockQProcess.return_value
        instance.state.return_value = MagicMock()  # NotRunning by default
        instance.processId.return_value = 0
        yield instance


@pytest.fixture
def mock_health_checker():
    """Return a mock HealthChecker that can emit status_changed."""
    checker = MagicMock()
    checker.check_once.return_value = False
    return checker
