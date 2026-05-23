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


START_OOPROXY_TEMPLATE = r"""<#
.SYNOPSIS
    Installs or removes the ooUI auto-start Scheduled Task.

.DESCRIPTION
    This script creates (or removes) a Windows Scheduled Task that launches
    the ooUI application (with the ooProxy server) at user logon, starting
    minimized in the system tray.

    -Install     Register the Scheduled Task.
    -Uninstall   Remove the Scheduled Task.

    The task runs the ooUI GUI application with ``--start-minimized`` flag,
    which initializes the proxy and minimizes the window to the system tray.
    It uses the ooUI project's own Python interpreter (``.venv\Scripts\python.exe``).

.PARAMETER Install
    Register the Scheduled Task.

.PARAMETER Uninstall
    Remove the Scheduled Task.

.EXAMPLE
    .\Start-OoProxy.ps1 -Install
    .\Start-OoProxy.ps1 -Uninstall
#>

param(
    [switch]$Install,
    [switch]$Uninstall
)

$TaskName = "ooProxy-AutoStart"
$TaskDesc = "Starts ooProxy Manager at user logon (minimized in system tray)"

# Get the path to the ooUI project root (parent of the ooproxy directory)
$OoProxyRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OoUIRoot = Split-Path -Parent $OoProxyRoot

# Prefer the bundled venv in ooUI; fall back to system python
$PythonExe = Join-Path $OoUIRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# Set working directory to ooUI root
$WorkingDir = $OoUIRoot

# Command to run: python -m gui.main --start-minimized
# This will start the ooUI application minimized in the system tray
$TaskAction = New-ScheduledTaskAction -Execute $PythonExe `
    -Argument "-m gui.main --start-minimized" `
    -WorkingDirectory $WorkingDir

$TaskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($Install) {
    Write-Output "Registering Scheduled Task '$TaskName'..."

    Register-ScheduledTask -TaskName $TaskName `
        -Action $TaskAction `
        -Trigger $TaskTrigger `
        -Settings $TaskSettings `
        -Principal $Principal `
        -Description $TaskDesc `
        -Force

    if ($?) {
        Write-Output "Scheduled Task '$TaskName' registered successfully."
        exit 0
    } else {
        Write-Error "Failed to register Scheduled Task '$TaskName'."
        exit 1
    }
}

if ($Uninstall) {
    Write-Output "Removing Scheduled Task '$TaskName'..."

    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        if ($?) {
            Write-Output "Scheduled Task '$TaskName' removed successfully."
            exit 0
        } else {
            Write-Error "Failed to remove Scheduled Task '$TaskName'."
            exit 1
        }
    } else {
        Write-Output "Scheduled Task '$TaskName' does not exist. Nothing to remove."
        exit 0
    }
}

# No switch provided — show usage
Write-Output "Usage: $($MyInvocation.MyCommand.Name) -Install | -Uninstall"
exit 1
"""


def set_ooproxy_home(path: str | Path) -> None:
    """Update the in-process ooProxy root. Called after config save or first-run."""
    global _ooproxy_home
    p = Path(path)
    if (p / "ooproxy.py").exists():
        _ooproxy_home = p
        # Automatically generate Start-OoProxy.ps1 if missing in the selected directory
        try:
            ps_script = p / "Start-OoProxy.ps1"
            if not ps_script.exists():
                ps_script.write_text(START_OOPROXY_TEMPLATE, encoding="utf-8")
        except Exception:
            pass



def get_ooproxy_home() -> Path | None:
    return _ooproxy_home


# ── Derived path helpers ──────────────────────────────────────────────────

def get_ooproxy_script() -> str:
    return str(_ooproxy_home / "ooproxy.py") if _ooproxy_home else ""


def get_ps1_script() -> str:
    """Get the path to Start-OoProxy.ps1, creating it if necessary.
    
    This function ensures the PowerShell script exists before returning its path.
    
    Returns:
        The full path to Start-OoProxy.ps1, or empty string if ooProxy home is not set.
    """
    if not _ooproxy_home:
        return ""
    
    try:
        return ensure_ps1_script()
    except Exception:
        # Fallback: return the path even if script creation failed
        return str(_ooproxy_home / "Start-OoProxy.ps1")


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


# ── PowerShell Script Bootstrap ───────────────────────────────────────────

def _get_ps1_script_content(ooui_root: Path) -> str:
    """Generate the Start-OoProxy.ps1 script content.
    
    Args:
        ooui_root: The ooUI project root directory.
        
    Returns:
        The PowerShell script content as a string.
    """
    return f"""<#
.SYNOPSIS
    Installs or removes the ooUI auto-start Scheduled Task.

.DESCRIPTION
    This script creates (or removes) a Windows Scheduled Task that launches
    the ooUI application (with the ooProxy server) at user logon, starting
    minimized in the system tray.

    -Install     Register the Scheduled Task.
    -Uninstall   Remove the Scheduled Task.

    The task runs the ooUI GUI application with ``--start-minimized`` flag,
    which initializes the proxy and minimizes the window to the system tray.
    It uses the ooUI project's own Python interpreter (``.venv\\Scripts\\python.exe``).

.PARAMETER Install
    Register the Scheduled Task.

.PARAMETER Uninstall
    Remove the Scheduled Task.

.EXAMPLE
    .\\Start-OoProxy.ps1 -Install
    .\\Start-OoProxy.ps1 -Uninstall
#>

param(
    [switch]$$Install,
    [switch]$$Uninstall
)

$$TaskName = "ooProxy-AutoStart"
$$TaskDesc = "Starts ooProxy Manager at user logon (minimized in system tray)"

# Get the path to the ooUI project root (parent of the ooproxy directory)
$$OoProxyRoot = Split-Path -Parent $$MyInvocation.MyCommand.Path
$$OoUIRoot = Split-Path -Parent $$OoProxyRoot

# Prefer the bundled venv in ooUI; fall back to system python
$$PythonExe = Join-Path $$OoUIRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $$PythonExe)) {{
    $$PythonExe = "python"
}}

# Set working directory to ooUI root
$$WorkingDir = $$OoUIRoot

# Command to run: python -m gui.main --start-minimized
# This will start the ooUI application minimized in the system tray
$$TaskAction = New-ScheduledTaskAction -Execute $$PythonExe `
    -Argument "-m gui.main --start-minimized" `
    -WorkingDirectory $$WorkingDir

$$TaskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $$env:USERNAME
$$TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$$Principal = New-ScheduledTaskPrincipal -UserId $$env:USERNAME -LogonType Interactive -RunLevel Limited

if ($$Install) {{
    Write-Output "Registering Scheduled Task '$$TaskName'..."

    Register-ScheduledTask -TaskName $$TaskName `
        -Action $$TaskAction `
        -Trigger $$TaskTrigger `
        -Settings $$TaskSettings `
        -Principal $$Principal `
        -Description $$TaskDesc `
        -Force

    if ($$?) {{
        Write-Output "Scheduled Task '$$TaskName' registered successfully."
        exit 0
    }} else {{
        Write-Error "Failed to register Scheduled Task '$$TaskName'."
        exit 1
    }}
}}

if ($$Uninstall) {{
    Write-Output "Removing Scheduled Task '$$TaskName'..."

    $$existing = Get-ScheduledTask -TaskName $$TaskName -ErrorAction SilentlyContinue
    if ($$existing) {{
        Unregister-ScheduledTask -TaskName $$TaskName -Confirm:$$false
        if ($$?) {{
            Write-Output "Scheduled Task '$$TaskName' removed successfully."
            exit 0
        }} else {{
            Write-Error "Failed to remove Scheduled Task '$$TaskName'."
            exit 1
        }}
    }} else {{
        Write-Output "Scheduled Task '$$TaskName' does not exist. Nothing to remove."
        exit 0
    }}
}}

# No switch provided — show usage
Write-Output "Usage: $$($$($$MyInvocation.MyCommand.Name)) -Install | -Uninstall"
exit 1
"""


def ensure_ps1_script() -> str:
    """Ensure the Start-OoProxy.ps1 script exists in the ooproxy root.
    
    Creates the script if it doesn't exist or if it's outdated.
    
    Returns:
        The full path to the Start-OoProxy.ps1 script.
        
    Raises:
        RuntimeError: If ooProxy home is not set.
    """
    if _ooproxy_home is None:
        raise RuntimeError("ooProxy home is not set")
    
    ps1_path = _ooproxy_home / "Start-OoProxy.ps1"
    
    # Get the ooUI root (parent of ooproxy)
    ooui_root = _ooproxy_home.parent
    
    # Generate the script content
    script_content = _get_ps1_script_content(ooui_root)
    
    # Write the script if it doesn't exist or needs updating
    try:
        ps1_path.write_text(script_content, encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to write Start-OoProxy.ps1: {e}")
    
    return str(ps1_path)


# Populate on import so the rest of the app can call get_ooproxy_home() immediately
_discovered = load_ooproxy_home()
if _discovered is not None:
    set_ooproxy_home(_discovered)
