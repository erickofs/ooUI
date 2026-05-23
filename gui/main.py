"""ooUI — Application entry point.

Launch with::

    python -m gui.main
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from gui import resources


def _ensure_ooproxy_home(app: QApplication) -> bool:
    """Return True if ooProxy home is set; show first-run dialog if not."""
    if resources.get_ooproxy_home() is not None:
        return True

    QMessageBox.information(
        None,
        "ooUI — First Run Setup",
        "ooUI needs to know where ooProxy is installed.\n\n"
        "Please select the folder that contains ooproxy.py.",
    )

    folder = QFileDialog.getExistingDirectory(
        None,
        "Select ooProxy installation folder",
        str(Path.home()),
    )

    if not folder:
        QMessageBox.critical(
            None,
            "ooUI",
            "No folder selected. Cannot start without ooProxy.",
        )
        return False

    if not (Path(folder) / "ooproxy.py").exists():
        QMessageBox.critical(
            None,
            "ooUI",
            f"ooproxy.py not found in:\n{folder}\n\n"
            "Please select the correct ooProxy installation folder.",
        )
        return False

    # Persist for future runs
    from gui.controllers.settings_controller import SettingsController
    ctrl = SettingsController()
    ctrl.save_ooproxy_home(folder)
    resources.set_ooproxy_home(folder)
    return True


def main() -> int:
    """Create and run the ooUI application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ooUI")
    app.setOrganizationName("ooUI")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)

    # Load ooProxy home from persisted config
    ooproxy_home = resources.load_ooproxy_home()
    if ooproxy_home:
        resources.set_ooproxy_home(ooproxy_home)

    if not _ensure_ooproxy_home(app):
        return 1

    # Ensure the PowerShell auto-start script exists
    try:
        resources.ensure_ps1_script()
    except Exception as e:
        # Log but don't fail — auto-start is optional
        print(f"[WARN] Failed to create Start-OoProxy.ps1: {e}")

    from gui.main_window import MainWindow
    
    # Check for --start-minimized flag
    start_minimized = "--start-minimized" in sys.argv
    
    window = MainWindow()
    if start_minimized:
        window.show_in_tray()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
