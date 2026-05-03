# ooProxy Manager (ooUI)

A PyQt6 desktop application for managing [ooProxy](https://github.com/MockbaTheBorg/ooProxy) — a lightweight local proxy that emulates an Ollama-compatible server while forwarding requests to any remote OpenAI-compatible backend.

## Overview

```
Client tool (e.g. VS Code Copilot Chat)
  (expects local server @ localhost:11434)
          │
          ▼
     ooProxy Manager
  (controls lifecycle, stores credentials)
          │
          ▼
       ooProxy
  (translates Ollama ↔ OpenAI format)
          │
          ▼
  Remote OpenAI-compatible API
  (NVIDIA NIM, OpenAI, Groq, Together AI,
   OpenRouter, Fireworks AI, Ollama, …)
```

ooProxy Manager provides a GUI layer on top of ooProxy: it starts and stops the proxy subprocess, stores API keys encrypted with Windows DPAPI, monitors proxy health, and exposes a settings UI so you never have to touch the command line.

---

## Features

| Feature | Description |
|---------|-------------|
| **Proxy lifecycle** | Start, stop, and restart ooProxy from the GUI |
| **Health monitoring** | Continuous background health checks with real-time status (Running / Stopped / Error) |
| **Encrypted key storage** | API keys are encrypted at rest using Windows DPAPI — keys never appear in plaintext on disk |
| **Auto-start on login** | Register ooProxy as a Windows Scheduled Task so it starts automatically at sign-in |
| **Real-time logs** | Stream proxy output to the Logs tab with export and clear controls |
| **Settings UI** | Configure backend URL, local port, API key, and UI language without editing files |
| **External tools** | Discover and run Python-based tools defined with JSON descriptors |
| **System tray** | Minimize to tray; restore or stop the proxy from the tray context menu |
| **Internationalization** | UI strings available in English (en_US) and Brazilian Portuguese (pt_BR) |
| **High-DPI support** | Pass-through DPI scaling for crisp rendering on HiDPI displays |

---

## Requirements

- **Operating system**: Windows 10/11 (DPAPI and PowerShell integration are Windows-only)
- **Python**: 3.10 or newer
- **Git**: required to clone with submodules

### Python dependencies (GUI)

```
PyQt6>=6.11.0
PyQt6-sip>=13.11.1
pytest          # development / testing only
pytest-qt       # development / testing only
pytest-cov      # development / testing only
```

### Python dependencies (ooProxy, in `ooproxy/`)

```
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
requests>=2.31.0
prompt_toolkit>=3.0.52
rich>=13.0.0
```

---

## Installation

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/<your-org>/ooUI.git
cd ooUI
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install GUI dependencies

```powershell
pip install PyQt6 PyQt6-sip
```

### 4. Install ooProxy dependencies

```powershell
pip install -r ooproxy\requirements.txt
```

---

## Running the Application

**Recommended (PowerShell launcher — sets the required `PYTHON_GIL=1` flag):**

```powershell
.\run.ps1
```

**Direct Python invocation:**

```powershell
python -m gui.main
# or
python gui/main.py
```

The window title is **ooProxy Manager**. On first launch it will prompt you for a backend URL and API key in the Settings tab.

---

## Usage

### Proxy tab

- Click **Start** to launch the ooProxy subprocess.
- The status bar at the bottom reflects the current proxy state (color-coded: green = Running, yellow = Starting/Stopping, red = Error).
- **Auto-start**: toggle registration of a Windows Scheduled Task that starts ooProxy at user sign-in.
- **Logs**: the log viewer streams all proxy output in real time. Use **Export** to save a text file, or **Clear** to wipe the buffer.

### Settings tab

| Field | Description |
|-------|-------------|
| Backend URL | Full URL of the remote OpenAI-compatible API (e.g. `https://integrate.api.nvidia.com/v1`) |
| Local port | Port ooProxy listens on locally (default `11434`) |
| API key | Your remote API key — stored encrypted with DPAPI |
| Language | `en_US` or `pt_BR` |

### Tools tab

Place Python tool scripts in the configured tools directory. Each tool must have a companion JSON descriptor. Click **Refresh** to rediscover tools, then select and run them from the list.

### Help tab

Quick-reference documentation available inside the application.

### System tray

Closing the window minimizes ooProxy Manager to the system tray. Right-click the tray icon to show/hide the window, stop the proxy, or quit the application entirely.

---

## Architecture

```
ooUI/
├── gui/
│   ├── main.py              # Application entry point (QApplication)
│   ├── main_window.py       # Root QMainWindow — tab composition + tray
│   ├── controllers/
│   │   ├── proxy_controller.py   # Proxy lifecycle, health checks, DPAPI
│   │   ├── settings_controller.py# Settings persistence
│   │   └── tools_controller.py   # Tool discovery and execution
│   ├── models/
│   │   ├── app_settings.py       # AppSettings dataclass
│   │   ├── proxy_state.py        # ProxyStatus enum + labels
│   │   └── tool_info.py          # ToolInfo dataclass
│   ├── workers/
│   │   ├── proxy_process.py      # QProcess wrapper for ooProxy subprocess
│   │   ├── health_checker.py     # Background health polling
│   │   ├── powershell_runner.py  # Windows PowerShell automation (DPAPI, tasks)
│   │   └── tool_runner.py        # External tool execution
│   ├── tabs/
│   │   ├── proxy_tab.py          # Proxy control + log viewer
│   │   ├── settings_tab.py       # Configuration form
│   │   ├── tools_tab.py          # Tool discovery + runner
│   │   └── help_tab.py           # Inline help
│   ├── i18n.py              # t() translation helper
│   ├── theme.py             # Dark palette + QSS stylesheet builder
│   ├── security.py          # Input validation + PowerShell encoding
│   └── resources.py         # Centralized path resolution
├── locales/
│   ├── en_US.json           # English translations
│   └── pt_BR.json           # Brazilian Portuguese translations
├── tests/                   # Unit and integration tests
├── ooproxy/                 # Git submodule — ooProxy server
├── docs/                    # Design documents and ADRs
└── run.ps1                  # PowerShell launcher
```

### Layer responsibilities

| Layer | Responsibility |
|-------|---------------|
| `controllers/` | Business logic — orchestrates models, workers, and Qt signals |
| `models/` | Pure data structures — no Qt, no I/O |
| `workers/` | Concurrency — QProcess, background threads, PowerShell runners |
| `gui/tabs/` | Presentation — Qt widgets wired to controller signals/slots |

Components communicate exclusively through Qt Signals/Slots, keeping layers decoupled.

---

## Security

All user-supplied and disk-read values pass through [security.py](gui/security.py) before being passed to any subprocess or external API.

| Function | Protects against |
|----------|-----------------|
| `validate_url` | Argument injection, non-HTTP(S) schemes |
| `validate_port` | Out-of-range or non-integer port values |
| `validate_endpoint` | Shell metacharacter injection in host strings |
| `validate_dpapi_blob` | On-disk tampering of encrypted key files |
| `encode_ps_command` | CWE-78 OS command injection via PowerShell metacharacters |
| `redact_key` | Accidental API key leakage in log output |

API keys are encrypted at rest using the Windows Data Protection API (DPAPI) via `ConvertTo-SecureString` / `ConvertFrom-SecureString`. Decryption is bound to the current Windows user account and machine — the ciphertext is useless outside that context.

---

## Internationalization

All UI strings are looked up through the `t()` helper in [gui/i18n.py](gui/i18n.py) using dot-notation keys (e.g. `t("tabs.proxy")`). Translation files live in `locales/`. To add a new locale, copy `locales/en_US.json`, translate the values, and add the language code to the settings options.

---

## Development

### Running tests

```powershell
pytest
# with coverage
pytest --cov=gui --cov-report=term-missing
```

Tests use `pytest-qt` fixtures and `unittest.mock` to isolate units from the real proxy process. Integration tests that require an actual ooProxy subprocess are opt-in.

### Code conventions

- Python 3.10+ idioms with `from __future__ import annotations` throughout.
- Business logic changes belong in `controllers/` and `workers/`, not in `gui/tabs/`.
- Every new UI string must go through `t()` and be added to both locale files.
- All inputs accepted from the user or read from disk must be validated through `security.py` before use.

---

## ooProxy submodule

The proxy server lives in `ooproxy/` as a Git submodule. See [ooproxy/README.md](ooproxy/README.md) for:

- Supported remote backends (NVIDIA NIM, OpenAI, Groq, Together AI, OpenRouter, Fireworks AI, Ollama, …)
- Cascade mode for multi-backend failover
- API endpoints exposed (`/api/chat`, `/v1/chat/completions`, `/v1/messages`, …)
- VS Code Copilot Chat integration guide
- Request caching configuration

To update the submodule to the latest upstream commit:

```bash
git submodule update --remote ooproxy
git add ooproxy
git commit -m "chore: bump ooproxy submodule"
```

---

## License

See [LICENSE](LICENSE) for details.
