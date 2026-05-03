"""Compatibility shim to re-export symbols from the root `security.py`.

Tests and modules import `gui.security`; the implementation lives at the
repository root in `security.py` — re-export the commonly used helpers.
"""
from importlib import import_module

_mod = import_module("security")

encode_ps_command = _mod.encode_ps_command
redact_key = _mod.redact_key
validate_dpapi_blob = _mod.validate_dpapi_blob
validate_endpoint = _mod.validate_endpoint
validate_port = _mod.validate_port
validate_url = _mod.validate_url

__all__ = [
    "encode_ps_command",
    "redact_key",
    "validate_dpapi_blob",
    "validate_endpoint",
    "validate_port",
    "validate_url",
]
