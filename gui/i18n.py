"""Compatibility shim for top-level `i18n.py`.

Some modules import `gui.i18n`; re-export the root `i18n` symbols here.
"""
from importlib import import_module

_mod = import_module("i18n")

# Common translation function used across the codebase
t = _mod.t

__all__ = ["t"]
