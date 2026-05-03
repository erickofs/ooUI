from unittest.mock import patch
from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])
from gui.controllers.proxy_controller import ProxyController


def test_debug_proxy_signal():
    with patch("gui.controllers.proxy_controller.HealthChecker"), patch("gui.controllers.proxy_controller.ProxyProcess") as MockProc:
        mock_proc = MockProc.return_value
        mock_proc.is_running.return_value = True
        ctrl = ProxyController()
        logs = []
        ctrl.log_received.connect(logs.append)
        ctrl.start_proxy("https://example.com", "key", 11434)
        print('DEBUG EMITTED LOGS:', logs)
        assert True
