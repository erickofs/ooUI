"""Centralized resource paths for ooUI.

ooProxy installation is discovered via (in order of precedence):
  1. ``~/.ooUI/config``  →  ``ooproxy_home`` field  (primary)
  2. ``OOPROXY_HOME``    env var                      (advanced override)
  3. ``<project_root>/ooproxy/``                      (bundled submodule)
  4. ``None``            — caller must handle (first-run dialog in main.py)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# ── ooUI config dir ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUI_DIR = Path(__file__).resolve().parent
OOUI_DIR = Path.home() / ".ooUI"
OOUI_CONFIG_FILE = OOUI_DIR / "config"

# API keys stay in the ooProxy-compatible format so ooProxy can also read them
OOPROXY_DIR = Path.home() / ".ooproxy"
OOPROXY_KEYS_FILE = OOPROXY_DIR / "keys"
OOPROXY_LOG_FILE = OOPROXY_DIR / "startup.log"
LEGACY_KEYS_DIR = Path.home() / ".ooProxy"
LEGACY_KEYS_FILE = LEGACY_KEYS_DIR / "keys.json"

ICON_PATH = PROJECT_ROOT / "icon.png"

# ── ooProxy root — resolved at import time, updated after first-run dialog ──
_ooproxy_home: Path | None = None


def load_ooproxy_home() -> Path | None:
    """Discover ooProxy installation without side-effects."""
    # 1. Persisted config
    if OOUI_CONFIG_FILE.exists():
        try:
            data = json.loads(OOUI_CONFIG_FILE.read_text(encoding="utf-8"))
            raw = data.get("ooproxy_home", "")
            if raw:
                p = Path(raw)
                if (p / "ooproxy.py").exists():
                    return p
        except Exception:
            pass
    # 2. Env var override
    env = os.environ.get("OOPROXY_HOME", "")
    if env:
        p = Path(env)
        if (p / "ooproxy.py").exists():
            return p
    # 3. Bundled git submodule
    bundled = PROJECT_ROOT / "ooproxy"
    if (bundled / "ooproxy.py").exists():
        return bundled
    return None


def set_ooproxy_home(path: str | Path) -> None:
    """Update the in-process ooProxy root. Called after config save or first-run."""
    global _ooproxy_home
    p = Path(path)
    if (p / "ooproxy.py").exists():
        _ooproxy_home = p


def get_ooproxy_home() -> Path | None:
    return _ooproxy_home


# ── Derived path helpers ──────────────────────────────────────────────────

def get_ooproxy_script() -> str:
    return str(_ooproxy_home / "ooproxy.py") if _ooproxy_home else ""


def get_ps1_script() -> str:
    return str(_ooproxy_home / "Start-OoProxy.ps1") if _ooproxy_home else ""


def get_python_path() -> str:
    if _ooproxy_home:
        venv = _ooproxy_home / "venv" / "Scripts" / "python.exe"
        if venv.exists():
            return str(venv)
    return "python"


def get_tool_scripts() -> list[dict[str, str]]:
    tools_dir = (_ooproxy_home / "tools") if _ooproxy_home else None
    if not tools_dir or not tools_dir.exists():
        return []
    tools = []
    for entry in sorted(tools_dir.iterdir()):
        if entry.suffix == ".py" and not entry.name.startswith("_"):
            label = entry.stem.replace("_", " ").title()
            tools.append({"name": label, "filename": entry.name, "path": str(entry)})
    return tools


# Populate on import so the rest of the app can call get_ooproxy_home() immediately
_discovered = load_ooproxy_home()
if _discovered is not None:
    set_ooproxy_home(_discovered)
