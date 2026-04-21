"""
Agent Tools Package
===================
Assembles TOOL_HANDLERS dict from all tool modules.
Key: tool name (function name without 'handle_' prefix)
Value: handler function
"""

from . import (
    instagram_tools,
    media_tools,
    analytics_tools,
    auth_tools,
    automation_tools,
    export_tools,
    file_tools,
    growth_tools,
    network_tools,
    pipeline_tools,
    system_tools,
    utility_tools,
    analysis_tools,
)

_TOOL_MODULES = [
    instagram_tools,
    media_tools,
    analytics_tools,
    auth_tools,
    automation_tools,
    export_tools,
    file_tools,
    growth_tools,
    network_tools,
    pipeline_tools,
    system_tools,
    utility_tools,
    analysis_tools,
]

TOOL_HANDLERS = {}
for _mod in _TOOL_MODULES:
    for _name in dir(_mod):
        if _name.startswith("handle_"):
            _func = getattr(_mod, _name)
            if callable(_func):
                TOOL_HANDLERS[_name[len("handle_"):]] = _func

__all__ = ["TOOL_HANDLERS"]
