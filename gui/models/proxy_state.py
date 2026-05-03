"""Compatibility shim: expose `models.proxy_state` as `gui.models.proxy_state`.

Some modules import the proxy state from `gui.models.proxy_state` while the
canonical implementation lives in `models/proxy_state.py`. Re-export the
symbols used by the UI and tests.
"""
from importlib import import_module

_mod = import_module("models.proxy_state")

ProxyStatus = _mod.ProxyStatus
ProxyInfo = _mod.ProxyInfo
STATUS_LABELS = _mod.STATUS_LABELS
get_status_label = _mod.get_status_label

__all__ = ["ProxyStatus", "ProxyInfo", "STATUS_LABELS", "get_status_label"]
