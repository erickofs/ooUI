"""Shim to expose `controllers.tools_controller` as `gui.controllers.tools_controller`.

This forwards public symbols so tests and imports that reference the
`gui.controllers.tools_controller` path continue to work.
"""
from importlib import import_module

_mod = import_module("controllers.tools_controller")

for _name in dir(_mod):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_mod, _name)

__all__ = [n for n in dir(_mod) if not n.startswith("_")]
