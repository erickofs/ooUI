"""Application settings model — backend URL, port, API keys, and ooProxy home."""

from __future__ import annotations

from dataclasses import dataclass, field


KNOWN_BACKENDS: list[dict[str, str]] = [
    {"name": "NVIDIA NIM", "url": "https://integrate.api.nvidia.com/v1"},
    {"name": "OpenAI", "url": "https://api.openai.com/v1"},
    {"name": "Groq", "url": "https://api.groq.com/openai/v1"},
    {"name": "Together AI", "url": "https://api.together.xyz/v1"},
    {"name": "OpenRouter", "url": "https://openrouter.ai/api/v1"},
    {"name": "Fireworks AI", "url": "https://api.fireworks.ai/inference/v1"},
]


@dataclass
class KeyEntry:
    """An API key entry for a specific endpoint."""

    endpoint: str
    key_encrypted: str
    key_plain: str = ""


@dataclass
class AppSettings:
    """Persistent application settings."""

    backend_url: str = "https://integrate.api.nvidia.com/v1"
    local_host: str = "127.0.0.1"
    local_port: int = 11434
    auto_start_enabled: bool = False
    language: str = "auto"
    ooproxy_home: str = ""
    keys: list[KeyEntry] = field(default_factory=list)
