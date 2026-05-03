"""Settings controller — reads/writes app configuration and API keys.

Config split:
  ~/.ooUI/config  — ooproxy_home, language  (ooUI-specific)
  ~/.ooproxy/keys — backend_url, API keys   (shared with ooProxy)
"""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from gui import resources
from gui.i18n import t
from gui.models.app_settings import AppSettings, KeyEntry, KNOWN_BACKENDS
from gui.resources import OOPROXY_KEYS_FILE, OOUI_CONFIG_FILE, OOUI_DIR, OOPROXY_DIR
from gui.security import validate_endpoint, validate_url
from gui.workers.powershell_runner import PowerShellRunner


class SettingsController(QObject):
    """Manages app settings and DPAPI key operations."""

    settings_loaded = pyqtSignal(object)
    key_saved = pyqtSignal(bool, str)
    key_deleted = pyqtSignal(bool, str)
    startup_status = pyqtSignal(bool)
    message = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = AppSettings()
        self._ps_runner = PowerShellRunner(self)

    @property
    def settings(self) -> AppSettings:
        return self._settings

    # ── Load / Save ───────────────────────────────────────────────────────

    def load_settings(self) -> None:
        """Load settings from ~/.ooUI/config and ~/.ooproxy/keys."""
        self._load_ooui_config()
        self._load_ooproxy_keys()
        self._check_startup_status()
        self.settings_loaded.emit(self._settings)

    def save_backend_url(self, url: str) -> None:
        try:
            url = validate_url(url)
        except ValueError as exc:
            self.message.emit(f"[ERROR] {exc}")
            return
        self._settings.backend_url = url.rstrip("/")
        self._persist_ooproxy_keys()
        self.message.emit(t("settings.url_updated", url=url))

    def save_port(self, port: int) -> None:
        self._settings.local_port = port
        self.message.emit(t("settings.port_updated", port=port))

    def save_language(self, lang: str) -> None:
        self._settings.language = lang
        self._persist_ooui_config()
        self.message.emit(t("settings.restart_required"))

    def save_ooproxy_home(self, path: str) -> None:
        """Persist the ooProxy installation folder to ~/.ooUI/config."""
        p = Path(path)
        if not (p / "ooproxy.py").exists():
            self.message.emit(t("settings.ooproxy_home_invalid"))
            return
        self._settings.ooproxy_home = str(p)
        self._persist_ooui_config()
        resources.set_ooproxy_home(p)
        self.message.emit(t("settings.ooproxy_home_updated"))

    # ── Key Management (DPAPI via PowerShell) ─────────────────────────────

    def add_key(self, endpoint: str, plain_key: str) -> None:
        if not endpoint or not plain_key:
            self.key_saved.emit(False, t("settings.key_required"))
            return
        try:
            endpoint = validate_endpoint(endpoint)
        except ValueError as exc:
            self.key_saved.emit(False, f"[ERROR] {exc}")
            return

        escaped = plain_key.replace("'", "''")
        ps_cmd = (
            f"$s = ConvertTo-SecureString '{escaped}' -AsPlainText -Force;"
            f"ConvertFrom-SecureString $s"
        )
        runner = PowerShellRunner(self)
        runner.finished.connect(
            lambda ok, out, err: self._on_key_encrypted(ok, out, err, endpoint)
        )
        runner.run_command(ps_cmd)

    def delete_key(self, endpoint: str) -> None:
        before = len(self._settings.keys)
        self._settings.keys = [k for k in self._settings.keys if k.endpoint != endpoint]
        if len(self._settings.keys) < before:
            self._persist_ooproxy_keys()
            self.key_deleted.emit(True, t("settings.key_deleted", endpoint=endpoint))
        else:
            self.key_deleted.emit(False, t("settings.key_not_found", endpoint=endpoint))

    def get_endpoints(self) -> list[str]:
        return [k.endpoint for k in self._settings.keys]

    # ── Scheduled Task ────────────────────────────────────────────────────

    def _check_startup_status(self) -> None:
        runner = PowerShellRunner(self)
        runner.finished.connect(self._on_startup_checked)
        runner.run_command(
            "Get-ScheduledTask -TaskName 'ooProxy-AutoStart' -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty State"
        )

    def _on_startup_checked(self, ok: bool, stdout: str, stderr: str) -> None:
        is_installed = ok and stdout.strip().lower() in ("ready", "running")
        self._settings.auto_start_enabled = is_installed
        self.startup_status.emit(is_installed)

    # ── Private helpers ───────────────────────────────────────────────────

    def _load_ooui_config(self) -> None:
        """Read ooproxy_home and language from ~/.ooUI/config."""
        if not OOUI_CONFIG_FILE.exists():
            return
        try:
            data = json.loads(OOUI_CONFIG_FILE.read_text(encoding="utf-8"))
            home = data.get("ooproxy_home", "")
            if home:
                self._settings.ooproxy_home = home
                resources.set_ooproxy_home(home)
            lang = data.get("language", "auto")
            self._settings.language = lang
        except Exception as exc:
            self.message.emit(t("settings.load_error", error=str(exc)))

    def _load_ooproxy_keys(self) -> None:
        """Read backend_url and API keys from ~/.ooproxy/keys."""
        if not OOPROXY_KEYS_FILE.exists():
            return
        try:
            raw = json.loads(OOPROXY_KEYS_FILE.read_text(encoding="utf-8"))
            url = raw.get("url", self._settings.backend_url)
            self._settings.backend_url = url
            keys = []
            for endpoint, encrypted in raw.get("entries", {}).items():
                keys.append(KeyEntry(endpoint=endpoint, key_encrypted=encrypted))
            self._settings.keys = keys
        except Exception as exc:
            self.message.emit(t("settings.load_error", error=str(exc)))

    def _persist_ooui_config(self) -> None:
        OOUI_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "ooproxy_home": self._settings.ooproxy_home,
            "language": self._settings.language,
        }
        OOUI_CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _persist_ooproxy_keys(self) -> None:
        OOPROXY_DIR.mkdir(parents=True, exist_ok=True)
        entries = {k.endpoint: k.key_encrypted for k in self._settings.keys}
        data = {
            "version": "v2-dpapi",
            "url": self._settings.backend_url,
            "entries": entries,
        }
        OOPROXY_KEYS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _on_key_encrypted(self, ok: bool, stdout: str, stderr: str, endpoint: str) -> None:
        if not ok or not stdout.strip():
            self.key_saved.emit(False, t("settings.key_encrypt_error", error=stderr))
            return
        encrypted = stdout.strip()
        found = False
        for key_entry in self._settings.keys:
            if key_entry.endpoint == endpoint:
                key_entry.key_encrypted = encrypted
                found = True
                break
        if not found:
            self._settings.keys.append(KeyEntry(endpoint=endpoint, key_encrypted=encrypted))
        self._persist_ooproxy_keys()
        self.key_saved.emit(True, t("settings.key_saved", endpoint=endpoint))
