"""Tests for SettingsController — key management and config persistence."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gui.controllers.settings_controller import SettingsController
from gui.models.app_settings import AppSettings, KeyEntry


class TestSettingsLoad:
    """Tests for loading settings from the keys file."""

    def test_load_empty_when_no_file(self, qtbot, tmp_path):
        """Settings are defaults when no keys file exists."""
        with patch("gui.controllers.settings_controller.OOPROXY_KEYS_FILE",
                    tmp_path / "nonexistent"):
            ctrl = SettingsController()
            signals = []
            ctrl.settings_loaded.connect(signals.append)
            ctrl.load_settings()

            assert len(signals) == 1
            settings = signals[0]
            assert isinstance(settings, AppSettings)
            assert settings.keys == []

    def test_load_reads_dpapi_keys(self, qtbot, tmp_path):
        """Settings are populated from a valid DPAPI keys file."""
        keys_file = tmp_path / "keys"
        data = {
            "version": "v2-dpapi",
            "url": "https://api.openai.com/v1",
            "entries": {
                "api.openai.com": "ENCRYPTED_VALUE_1",
                "api.groq.com": "ENCRYPTED_VALUE_2",
            },
        }
        keys_file.write_text(json.dumps(data), encoding="utf-8")

        with patch("gui.controllers.settings_controller.OOPROXY_KEYS_FILE", keys_file), \
             patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            signals = []
            ctrl.settings_loaded.connect(signals.append)
            ctrl.load_settings()

            settings = signals[0]
            assert settings.backend_url == "https://api.openai.com/v1"
            assert len(settings.keys) == 2
            endpoints = {k.endpoint for k in settings.keys}
            assert "api.openai.com" in endpoints
            assert "api.groq.com" in endpoints


class TestSettingsSave:
    """Tests for saving configuration."""

    def test_save_backend_url(self, qtbot, tmp_path):
        """Saving URL updates settings and persists to file."""
        keys_file = tmp_path / "keys"
        ooproxy_dir = tmp_path

        with patch("gui.controllers.settings_controller.OOPROXY_KEYS_FILE", keys_file), \
             patch("gui.controllers.settings_controller.OOPROXY_DIR", ooproxy_dir):
            ctrl = SettingsController()
            ctrl.save_backend_url("https://api.together.xyz/v1")

            assert ctrl.settings.backend_url == "https://api.together.xyz/v1"
            # Check file was written
            assert keys_file.exists()
            data = json.loads(keys_file.read_text(encoding="utf-8"))
            assert data["url"] == "https://api.together.xyz/v1"

    def test_save_port(self, qtbot):
        """Saving port updates settings in memory."""
        with patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            messages = []
            ctrl.message.connect(messages.append)

            ctrl.save_port(8080)
            assert ctrl.settings.local_port == 8080
            assert any("8080" in m for m in messages)


class TestKeyManagement:
    """Tests for add/delete key operations."""

    def test_add_key_empty_endpoint_fails(self, qtbot):
        """Adding a key with empty endpoint emits failure."""
        with patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            results = []
            ctrl.key_saved.connect(lambda ok, msg: results.append((ok, msg)))
            ctrl.add_key("", "some-key")
            assert results[0][0] is False

    def test_add_key_empty_key_fails(self, qtbot):
        """Adding a key with empty value emits failure."""
        with patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            results = []
            ctrl.key_saved.connect(lambda ok, msg: results.append((ok, msg)))
            ctrl.add_key("example.com", "")
            assert results[0][0] is False

    def test_delete_existing_key(self, qtbot, tmp_path):
        """Deleting an existing key removes it and persists."""
        keys_file = tmp_path / "keys"

        with patch("gui.controllers.settings_controller.OOPROXY_KEYS_FILE", keys_file), \
             patch("gui.controllers.settings_controller.OOPROXY_DIR", tmp_path):
            ctrl = SettingsController()
            ctrl._settings.keys = [
                KeyEntry(endpoint="api.openai.com", key_encrypted="ENC1"),
                KeyEntry(endpoint="api.groq.com", key_encrypted="ENC2"),
            ]

            results = []
            ctrl.key_deleted.connect(lambda ok, msg: results.append((ok, msg)))
            ctrl.delete_key("api.openai.com")

            assert results[0][0] is True
            assert len(ctrl.settings.keys) == 1
            assert ctrl.settings.keys[0].endpoint == "api.groq.com"

    def test_delete_nonexistent_key(self, qtbot):
        """Deleting a non-existent key emits failure."""
        with patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            results = []
            ctrl.key_deleted.connect(lambda ok, msg: results.append((ok, msg)))
            ctrl.delete_key("nonexistent.com")
            assert results[0][0] is False

    def test_get_endpoints(self, qtbot):
        """get_endpoints returns a list of configured endpoints."""
        with patch("gui.controllers.settings_controller.PowerShellRunner"):
            ctrl = SettingsController()
            ctrl._settings.keys = [
                KeyEntry(endpoint="a.com", key_encrypted="x"),
                KeyEntry(endpoint="b.com", key_encrypted="y"),
            ]
            assert ctrl.get_endpoints() == ["a.com", "b.com"]
