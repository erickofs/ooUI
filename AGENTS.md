# AGENTS for ooUI

## Purpose
This file helps AI coding agents understand the ooUI repository quickly and act on changes with minimal context.

## Project overview
- Python desktop application using **PyQt6** for managing an ooProxy server.
- Key concerns: proxy lifecycle, health checking, settings persistence, tool execution, and Windows DPAPI key storage.
- The app is primarily organized into `models/`, `controllers/`, `workers/`, and `gui/` packages.

## Run commands
- Start the application:
  - `python -m gui.main`
  - or `python gui/main.py`
- Run tests:
  - `pytest`

## Important files and directories
- `gui/main.py` — application entrypoint that builds the Qt app and main window.
- `main_window.py` — root QMainWindow with tab composition.
- `controllers/proxy_controller.py` — main proxy lifecycle orchestration.
- `workers/proxy_process.py` — subprocess wrapper for `ooproxy.py`.
- `workers/health_checker.py` — background health polling logic.
- `security.py` — input validation and Windows DPAPI support.
- `models/app_settings.py` — stored settings and backend configuration.
- `tests/conftest.py` — PyQt `QApplication` fixture and test setup.

## Conventions for AI agents
- Prefer changing business logic in `controllers/` and `workers/`, not UI widgets in `gui/tabs/`, unless the change is specifically UI-related.
- Use `pytest` and existing mocks for tests. Avoid adding integration tests that require a real `ooproxy.py` process unless the feature explicitly targets process launching.
- Preserve the translation system in `i18n.py`; textual UI strings are mapped through translation keys.
- Keep Python 3.10+ idioms and `from __future__ import annotations` style consistent.

## Notes
- There is no existing `README.md` in the repository root.
- The project expects Windows-specific behavior for DPAPI encryption and PowerShell tool execution.
