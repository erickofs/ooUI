"""Shim to expose `models.tool_info` as `gui.models.tool_info`.

For compatibility with imports in the GUI code and tests, re-export the
`ToolInfo` dataclass and `enrich_tool_info` helper from the canonical
`models.tool_info` module.
"""
from importlib import import_module

_mod = import_module("models.tool_info")

ToolInfo = _mod.ToolInfo
enrich_tool_info = _mod.enrich_tool_info

__all__ = ["ToolInfo", "enrich_tool_info"]
