"""Shim for `workers.tool_runner` as `gui.workers.tool_runner`.
"""
from importlib import import_module

_mod = import_module("workers.tool_runner")

ToolRunner = _mod.ToolRunner

__all__ = ["ToolRunner"]
