"""Security tests — validates input sanitisation, injection prevention,
secret redaction, and absence of ``shell=True`` across the codebase.

Test contracts follow the Given/When/Then format from the security audit.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from gui.security import (
    encode_ps_command,
    redact_key,
    validate_dpapi_blob,
    validate_endpoint,
    validate_port,
    validate_url,
)


# ── Ensure a QApplication exists for Qt plumbing ─────────────────────

@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# =====================================================================
# T1: Port Injection
# GIVEN a validate_port function
# WHEN  the user supplies malicious or out-of-range values
# THEN  ValueError MUST be raised
# =====================================================================


class TestPortValidation:
    """T1: Injection and abuse via the port field."""

    def test_valid_port(self):
        assert validate_port(11434) == 11434

    def test_valid_port_string(self):
        assert validate_port("8080") == 8080

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="between 1024 and 65535"):
            validate_port(-1)

    def test_rejects_privileged_port(self):
        with pytest.raises(ValueError, match="between 1024 and 65535"):
            validate_port(80)

    def test_rejects_above_max(self):
        with pytest.raises(ValueError, match="between 1024 and 65535"):
            validate_port(70000)

    def test_rejects_injection_string(self):
        with pytest.raises(ValueError, match="integer"):
            validate_port("11434; rm -rf /")

    def test_rejects_newline_injection(self):
        with pytest.raises(ValueError, match="integer"):
            validate_port("11434\nmalicious")

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="integer"):
            validate_port(None)


# =====================================================================
# T2: URL Injection
# GIVEN a validate_url function
# WHEN  the user supplies argument-injection or malformed URLs
# THEN  ValueError MUST be raised
# =====================================================================


class TestURLValidation:
    """T2: Command injection and protocol abuse via URL field."""

    def test_valid_https_url(self):
        result = validate_url("https://integrate.api.nvidia.com/v1")
        assert result == "https://integrate.api.nvidia.com/v1"

    def test_valid_http_url(self):
        result = validate_url("http://localhost:8080")
        assert result.startswith("http://")

    def test_rejects_argument_injection(self):
        with pytest.raises(ValueError, match="dash"):
            validate_url("--url=; calc.exe")

    def test_rejects_javascript_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("javascript:alert(1)")

    def test_rejects_file_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("ftp://evil.com/payload")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_url("")

    def test_rejects_no_host(self):
        with pytest.raises(ValueError, match="hostname"):
            validate_url("https://")

    def test_rejects_bare_words(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_url("not-a-url")


# =====================================================================
# T3: API Key Injection (EncodedCommand)
# GIVEN the PowerShellRunner
# WHEN  a malicious key value is processed
# THEN  it MUST be encoded with Base64 (EncodedCommand), not raw -Command
# =====================================================================


class TestEncodedCommand:
    """T3: PowerShell commands are Base64-encoded, preventing injection."""

    def test_encoding_produces_base64(self):
        result = encode_ps_command("Write-Host 'hello'")
        # Must be valid Base64 (ASCII chars, no shell metacharacters)
        assert re.match(r"^[A-Za-z0-9+/=]+$", result)

    def test_injection_attempt_is_harmless(self):
        # The attacker's payload becomes part of a Base64-encoded binary blob
        malicious = "key'; Invoke-WebRequest http://evil.com; '"
        script = f"$s = ConvertTo-SecureString '{malicious}' -AsPlainText -Force"
        encoded = encode_ps_command(script)
        # The encoded result must NOT contain the original shell metacharacters
        assert ";" not in encoded
        assert "Invoke-WebRequest" not in encoded

    def test_encoded_command_not_empty(self):
        with pytest.raises(ValueError, match="empty"):
            encode_ps_command("")

    def test_runner_uses_encoded_command(self):
        """Verify the PowerShellRunner uses -EncodedCommand, not -Command."""
        from gui.workers.powershell_runner import PowerShellRunner
        runner = PowerShellRunner()
        with patch.object(runner, "_run") as mock_run:
            runner.run_command("Write-Host 'test'")
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            ps_args = args[1]  # The list of arguments
            assert "-EncodedCommand" in ps_args
            assert "-Command" not in ps_args


# =====================================================================
# T4: DPAPI Blob Tampering
# GIVEN the validate_dpapi_blob function
# WHEN  the blob from disk contains non-hex characters (tampering)
# THEN  ValueError MUST be raised
# =====================================================================


class TestDPAPIBlobValidation:
    """T4: DPAPI blob integrity validation."""

    def test_valid_hex_blob(self):
        blob = "01000000d08c9ddf0115d1118c7a00c04fc297eb"
        assert validate_dpapi_blob(blob) == blob

    def test_rejects_injection_in_blob(self):
        with pytest.raises(ValueError, match="non-hex|tampering"):
            validate_dpapi_blob("abc123'; calc.exe; '")

    def test_rejects_semicolons(self):
        with pytest.raises(ValueError, match="non-hex|tampering"):
            validate_dpapi_blob("abc123;rm -rf /")

    def test_rejects_newlines(self):
        with pytest.raises(ValueError, match="non-hex|tampering"):
            validate_dpapi_blob("abc123\nInvoke-Danger")

    def test_rejects_powershell_subexpression(self):
        with pytest.raises(ValueError, match="non-hex|tampering"):
            validate_dpapi_blob("abc$(malicious)")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="non-hex|tampering"):
            validate_dpapi_blob("abc 123")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_dpapi_blob("")

    def test_controller_rejects_tampered_blob(self):
        """Integration: proxy controller rejects tampered DPAPI blob."""
        from gui.controllers.proxy_controller import ProxyController
        ctrl = ProxyController()

        log_messages: list[str] = []
        ctrl.log_received.connect(log_messages.append)

        with patch.object(ctrl, "_read_dpapi_encrypted_key", return_value="abc'; calc; '"):
            ctrl.start_proxy_with_dpapi("https://api.example.com/v1")

        assert any("tampering" in msg.lower() for msg in log_messages)


# =====================================================================
# T5: Key Leakage in Logs
# GIVEN the proxy is running with a secret key
# WHEN  log output passes through _on_output
# THEN  the key MUST be redacted
# =====================================================================


class TestKeyRedaction:
    """T5: API keys must never leak into log output."""

    def test_redact_key_replaces_secret(self):
        text = "Using key sk-secret123 for auth"
        result = redact_key(text, "sk-secret123")
        assert "sk-secret123" not in result
        assert "***REDACTED***" in result

    def test_redact_key_noop_when_empty(self):
        text = "No key here"
        assert redact_key(text, "") == text

    def test_redact_key_handles_multiple_occurrences(self):
        text = "key=ABC retry with key=ABC"
        result = redact_key(text, "ABC")
        assert result.count("***REDACTED***") == 2
        assert "ABC" not in result

    def test_proxy_controller_redacts_output(self):
        """Integration: key in process output is redacted before log signal."""
        from gui.controllers.proxy_controller import ProxyController
        ctrl = ProxyController()
        ctrl._key = "sk-secret-api-key-12345"

        log_messages: list[str] = []
        ctrl.log_received.connect(log_messages.append)

        # Simulate process output containing the key
        ctrl._on_output("INFO: Authenticating with sk-secret-api-key-12345")

        assert len(log_messages) == 1
        assert "sk-secret-api-key-12345" not in log_messages[0]
        assert "***REDACTED***" in log_messages[0]


# =====================================================================
# T6: PS Error Handling (no stack traces, no freeze)
# GIVEN a failed PowerShell execution
# WHEN  the result is processed
# THEN  the UI must handle it gracefully (ERROR status, safe message)
# =====================================================================


class TestErrorHandling:
    """T6: Secure error handling for PowerShell failures."""

    def test_dpapi_failure_sets_error_status(self):
        from gui.models.proxy_state import ProxyStatus
        from gui.controllers.proxy_controller import ProxyController
        ctrl = ProxyController()

        statuses: list = []
        ctrl.status_changed.connect(statuses.append)

        log_messages: list[str] = []
        ctrl.log_received.connect(log_messages.append)

        # Simulate DPAPI decryption failure
        ctrl._status = ProxyStatus.STARTING
        ctrl._on_dpapi_decrypted(False, "", "Access Denied")

        assert ctrl.get_status() == ProxyStatus.ERROR

    def test_invalid_url_does_not_crash(self):
        from gui.controllers.proxy_controller import ProxyController
        ctrl = ProxyController()

        log_messages: list[str] = []
        ctrl.log_received.connect(log_messages.append)

        # Pass a clearly invalid URL — should not raise, should log error
        ctrl.start_proxy("not-a-valid-url", "", 11434)

        assert any("error" in msg.lower() for msg in log_messages)

    def test_invalid_port_does_not_crash(self):
        from gui.controllers.proxy_controller import ProxyController
        ctrl = ProxyController()

        log_messages: list[str] = []
        ctrl.log_received.connect(log_messages.append)

        ctrl.start_proxy("https://api.example.com/v1", "", 99999)

        assert any("error" in msg.lower() for msg in log_messages)


# =====================================================================
# T7: No shell=True in Codebase
# GIVEN the entire gui/ codebase
# WHEN  we scan for shell=True
# THEN  there MUST be zero occurrences
# =====================================================================


class TestNoShellTrue:
    """T7: Audit — no shell=True anywhere in the codebase."""

    def test_no_shell_true_in_gui(self):
        gui_dir = Path(__file__).resolve().parents[1] / "gui"
        violations = []
        for py_file in gui_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Skip comments and docstrings (lines starting with # or """)
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                # Only flag actual code usage: shell=True as a keyword arg
                if re.search(r'shell\s*=\s*True', line):
                    violations.append(f"{py_file.name}:{i}: {stripped}")

        assert violations == [], (
            f"Found shell=True in the following locations:\n"
            + "\n".join(violations)
        )

    def test_no_os_system_in_gui(self):
        gui_dir = Path(__file__).resolve().parents[1] / "gui"
        violations = []
        for py_file in gui_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if "os.system(" in line and not line.strip().startswith("#"):
                    violations.append(f"{py_file.name}:{i}: {line.strip()}")

        assert violations == [], (
            f"Found os.system() in the following locations:\n"
            + "\n".join(violations)
        )


# =====================================================================
# Endpoint Validation (bonus: from settings controller)
# =====================================================================


class TestEndpointValidation:
    """Endpoint format validation — blocks shell metacharacters."""

    def test_valid_endpoint(self):
        assert validate_endpoint("api.example.com") == "api.example.com"

    def test_valid_endpoint_with_port(self):
        assert validate_endpoint("api.example.com:443") == "api.example.com:443"

    def test_rejects_semicolons(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_endpoint("api.example.com; rm -rf /")

    def test_rejects_pipe(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_endpoint("api.example.com | evil")

    def test_rejects_dollar_sign(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_endpoint("$(calc.exe)")

    def test_rejects_backtick(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_endpoint("api`evil")

    def test_rejects_quotes(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_endpoint("api'evil")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_endpoint("")
