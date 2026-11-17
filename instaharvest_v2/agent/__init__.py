"""
Agent Package
=============
Natural-language Instagram automation and multi-agent coordination.
"""

from typing import Any


_LAZY_EXPORTS = {
    "InstaAgent": (".core", "InstaAgent"),
    "AgentResult": (".core", "AgentResult"),
    "Permission": (".permissions", "Permission"),
    "AgentCoordinator": (".coordinator", "AgentCoordinator"),
    "CoordinatorResult": (".coordinator", "CoordinatorResult"),
}

__all__ = list(_LAZY_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    """Lazy-load agent exports on demand."""
    spec = _LAZY_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module 'instaharvest_v2.agent' has no attribute {name!r}")
    mod_path, attr_name = spec
    import importlib
    mod = importlib.import_module(mod_path, package=__name__)
    val = getattr(mod, attr_name)
    globals()[name] = val
    return val
