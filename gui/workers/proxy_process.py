"""Shim for `workers.proxy_process` as `gui.workers.proxy_process`.
"""
from importlib import import_module

_mod = import_module("workers.proxy_process")

ProxyProcess = _mod.ProxyProcess

__all__ = ["ProxyProcess"]
