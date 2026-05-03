"""Shim for `workers.health_checker` as `gui.workers.health_checker`.

This module re-exports the public symbols from the canonical
``workers.health_checker`` implementation so tests that patch
``gui.workers.health_checker.urllib.request.urlopen`` can find the
``urllib`` attribute on this module.
"""
from importlib import import_module

_mod = import_module("workers.health_checker")

for _name in dir(_mod):
	if not _name.startswith("_"):
		globals()[_name] = getattr(_mod, _name)

__all__ = [n for n in dir(_mod) if not n.startswith("_")]
