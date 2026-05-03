"""Shim for `workers.powershell_runner` as `gui.workers.powershell_runner`.
"""
from importlib import import_module

_mod = import_module("workers.powershell_runner")

PowerShellRunner = _mod.PowerShellRunner

__all__ = ["PowerShellRunner"]
