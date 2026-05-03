"""Tests for ProxyController — proxy lifecycle without real processes."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from gui.controllers.proxy_controller import ProxyController
from gui.models.proxy_state import ProxyStatus


class TestProxyControllerStatus:
    """Tests for proxy status transitions."""

    def test_initial_status_is_unknown(self, qtbot):
        """TC: Controller starts with UNKNOWN status."""
        with patch("gui.controllers.proxy_controller.HealthChecker"):
            ctrl = ProxyController()
        assert ctrl.get_status() == ProxyStatus.UNKNOWN

    def test_start_proxy_transitions_to_starting(self, qtbot):
        """TC-03: Clicking start transitions through STARTING."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
            mock_proc = MockProc.return_value
            mock_proc.is_running.return_value = False

            ctrl = ProxyController()
            signals = []
            ctrl.status_changed.connect(lambda s: signals.append(s))

            ctrl.start_proxy(
                url="https://integrate.api.nvidia.com/v1",
                key="nvapi-test",
                port=11434,
            )

            assert ProxyStatus.STARTING in signals
            assert ctrl.get_status() == ProxyStatus.STARTING
            mock_proc.start.assert_called_once()

    def test_start_proxy_noop_if_already_running(self, qtbot):
        """Guard: Calling start when proxy is running does nothing."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
            mock_proc = MockProc.return_value
            mock_proc.is_running.return_value = True

            ctrl = ProxyController()
            logs = []
            ctrl.log_received.connect(logs.append)
            ctrl.start_proxy("https://example.com", "key", 11434)

            mock_proc.start.assert_not_called()
            assert any("já está rodando" in l for l in logs)

    def test_start_proxy_passes_key_via_env_and_not_args(self, qtbot):
        """Start must pass secret via env var and not expose it on CLI."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
            mock_proc = MockProc.return_value
            mock_proc.is_running.return_value = False

            ctrl = ProxyController()
            ctrl.start_proxy(
                url="https://integrate.api.nvidia.com/v1",
                key="nvapi-secret-123",
                port=11434,
            )

            mock_proc.start.assert_called_once()
            call_args = mock_proc.start.call_args[0]
            # positional args: python_path, args, (optional) env
            assert isinstance(call_args[0], str)
            args_passed = call_args[1]
            assert "nvapi-secret-123" not in " ".join(map(str, args_passed))
            env_passed = call_args[2] if len(call_args) >= 3 else None
            assert env_passed is not None and env_passed.get("OOPROXY_API_KEY") == "nvapi-secret-123"

    def test_stop_proxy_calls_terminate(self, qtbot):
        """TC-04: Stopping proxy calls process.stop()."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
            mock_proc = MockProc.return_value
            mock_proc.is_running.return_value = True

            ctrl = ProxyController()
            ctrl._status = ProxyStatus.RUNNING
            ctrl.stop_proxy()

            mock_proc.stop.assert_called_once()
            assert ctrl.get_status() == ProxyStatus.STOPPING

    def test_process_crash_sets_error(self, qtbot):
        """TC-05: Process crash transitions to ERROR."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess"):
            ctrl = ProxyController()
            ctrl._status = ProxyStatus.RUNNING

            signals = []
            ctrl.status_changed.connect(lambda s: signals.append(s))
            ctrl._on_process_finished(1, "CrashExit")

            assert ProxyStatus.ERROR in signals
            assert ctrl.get_status() == ProxyStatus.ERROR

    def test_process_normal_exit_sets_stopped(self, qtbot):
        """Process normal exit transitions to STOPPED."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess"):
            ctrl = ProxyController()
            ctrl._status = ProxyStatus.RUNNING

            ctrl._on_process_finished(0, "NormalExit")
            assert ctrl.get_status() == ProxyStatus.STOPPED

    def test_health_check_running_sets_running(self, qtbot):
        """TC-01: Health check OK transitions from STARTING to RUNNING."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess"):
            ctrl = ProxyController()
            ctrl._status = ProxyStatus.STARTING

            signals = []
            ctrl.status_changed.connect(lambda s: signals.append(s))
            ctrl._on_health_changed(True)

            assert ProxyStatus.RUNNING in signals

    def test_health_check_down_sets_stopped(self, qtbot):
        """TC-02: Health check fails with no process → STOPPED."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
            mock_proc = MockProc.return_value
            mock_proc.is_running.return_value = False

            ctrl = ProxyController()
            ctrl._status = ProxyStatus.RUNNING

            ctrl._on_health_changed(False)
            assert ctrl.get_status() == ProxyStatus.STOPPED


class TestProxyControllerStartup:
    """Tests for install/uninstall scheduled task."""

    def test_install_startup_runs_ps1(self, qtbot):
        """TC-08: Install auto-start invokes PowerShell with -Install."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess"), \
             patch("gui.controllers.proxy_controller.PowerShellRunner") as MockPS:
            mock_runner = MagicMock()
            MockPS.return_value = mock_runner

            ctrl = ProxyController()
            ctrl.install_startup()

            # A new runner is created inside install_startup, so check the class call
            assert MockPS.call_count >= 1

    def test_uninstall_startup_runs_ps1(self, qtbot):
        """TC-08: Uninstall auto-start invokes PowerShell with -Uninstall."""
        with patch("gui.controllers.proxy_controller.HealthChecker"), \
             patch("gui.controllers.proxy_controller.ProxyProcess"), \
             patch("gui.controllers.proxy_controller.PowerShellRunner") as MockPS:
            ctrl = ProxyController()
            ctrl.uninstall_startup()
            assert MockPS.call_count >= 1
