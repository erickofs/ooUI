"""Compatibility shim: expose the top-level `controllers.proxy_controller`.

Some parts of the test-suite and imports expect the module
``gui.controllers.proxy_controller``. The real implementation lives in
``controllers/proxy_controller.py`` (top-level). Import that module and
re-export the `ProxyController` class so both import paths work.
"""
from importlib import import_module

# Import the real implementation and re-export its public symbols so that
# patching and imports that target `gui.controllers.proxy_controller` work
# as if the module lived here.
_mod = import_module("controllers.proxy_controller")

for _name in dir(_mod):
	if not _name.startswith("_"):
		globals()[_name] = getattr(_mod, _name)

# Wrap the real ProxyController so that tests which patch
# `gui.controllers.proxy_controller.ProxyProcess` and
# `gui.controllers.proxy_controller.HealthChecker` will be respected by
# the underlying implementation: before instantiating the real controller
# we temporarily inject the (possibly patched) classes into the original
# module namespace so the real __init__ uses them.
_orig_mod = _mod
_RealProxyController = globals().get("ProxyController")


class ProxyController(_RealProxyController):
	def __init__(self, parent=None):
		orig_proc = getattr(_orig_mod, "ProxyProcess", None)
		orig_health = getattr(_orig_mod, "HealthChecker", None)
		try:
			if "ProxyProcess" in globals():
				setattr(_orig_mod, "ProxyProcess", globals()["ProxyProcess"])
			if "HealthChecker" in globals():
				setattr(_orig_mod, "HealthChecker", globals()["HealthChecker"])
			super().__init__(parent)
		finally:
			if orig_proc is not None:
				setattr(_orig_mod, "ProxyProcess", orig_proc)
			if orig_health is not None:
				setattr(_orig_mod, "HealthChecker", orig_health)


__all__ = [n for n in dir(_mod) if not n.startswith("_")]
