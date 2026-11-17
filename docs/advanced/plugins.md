# Plugin System

InstaHarvest v2 provides a lifecycle hook `Plugin` interface managed by `PluginManager`. Plugins attach via `ig.use(plugin)` and subscribe automatically to `EventEmitter` events (`REQUEST`, `ERROR`, `RETRY`, `RATE_LIMIT`, `CHALLENGE`, `LOGIN_REQUIRED`).

## Quick Example

```python
from instaharvest_v2 import Instagram, Plugin

class RequestLoggerPlugin(Plugin):
    name = "request_logger"
    version = "1.0.0"

    def on_install(self, ig):
        self.ig = ig
        print(f"Plugin {self.name} installed!")

    def on_request(self, event):
        print(f"📡 Request -> {event.endpoint}")

    def on_rate_limit(self, event):
        print(f"⏳ Rate limited on {event.endpoint} (attempt {event.attempt})")

ig = Instagram.from_env()
ig.use(RequestLoggerPlugin())
```

## Available Lifecycle Hooks

Subclass `instaharvest_v2.plugin.Plugin` (re-exported as `instaharvest_v2.Plugin`) and override any of the following hooks:

| Hook | Triggered On | Argument |
|---|---|---|
| `on_install(self, ig)` | `ig.use(plugin)` | `Instagram` / `AsyncInstagram` instance |
| `on_uninstall(self)` | `ig.remove_plugin(name)` | — |
| `on_request(self, event)` | `EventType.REQUEST` | `EventData` |
| `on_response(self, event)` | Subscribed response hook | `EventData` |
| `on_error(self, event)` | `EventType.ERROR` | `EventData` |
| `on_retry(self, event)` | `EventType.RETRY` | `EventData` |
| `on_rate_limit(self, event)` | `EventType.RATE_LIMIT` | `EventData` |
| `on_challenge(self, event)` | `EventType.CHALLENGE` | `EventData` |
| `on_login_required(self, event)` | `EventType.LOGIN_REQUIRED` | `EventData` |

## Managing Plugins

```python
# Access an installed plugin via PluginManager
plugin = ig._plugin_mgr.get_plugin("request_logger")

# List all installed plugins
installed = ig._plugin_mgr.list_plugins()

# Uninstall by name
ig.remove_plugin("request_logger")
```
