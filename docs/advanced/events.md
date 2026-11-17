# Event System

InstaHarvest v2 includes a built-in `EventEmitter` (`ig._events`) supporting both **synchronous and async callbacks** across request, retry, rate-limit, and rotation lifecycles.

## Quick Example

```python
from instaharvest_v2 import Instagram
from instaharvest_v2.events import EventType

def on_request(event):
    print(f"📡 Requesting: {event.endpoint}")

def on_challenge(event):
    print(f"🚨 Challenge on {event.endpoint}: {event.error}")

ig = Instagram.from_env()

# Hook into events via EventType or raw string value
ig.on(EventType.REQUEST, on_request)
ig.on(EventType.CHALLENGE, on_challenge)
```

## Available Event Types

`instaharvest_v2.events.EventType` defines all emitted event types, each passing an `EventData` dataclass (`event_type`, `timestamp`, `attempt`, `endpoint`, `error`, `status_code`, `extra`) to registered handlers:

| Enum Member | Value | When Fired |
|---|---|---|
| `EventType.REQUEST` | `"request"` | On HTTP request execution |
| `EventType.RETRY` | `"retry"` | Before retrying a failed request |
| `EventType.RATE_LIMIT` | `"rate_limit"` | When HTTP 429 / rate limit occurs |
| `EventType.CHALLENGE` | `"challenge"` | When `ChallengeRequired` is triggered |
| `EventType.LOGIN_REQUIRED` | `"login_required"` | When session auth expires (401/302) |
| `EventType.NETWORK_ERROR` | `"network_error"` | On connection/transport failure |
| `EventType.ERROR` | `"error"` | On general request error |
| `EventType.SESSION_REFRESH` | `"session_refresh"` | On session auto-refresh attempt |
| `EventType.SESSION_ROTATE` | `"session_rotate"` | On multi-session rotation |
| `EventType.PROXY_ROTATE` | `"proxy_rotate"` | On proxy switch |

## Using `EventEmitter`

You can listen (`.on`) and unregister (`.off`) directly on `Instagram` / `AsyncInstagram`:

### Monitor Request Throughput

```python
import time
from instaharvest_v2 import Instagram
from instaharvest_v2.events import EventType

class SpeedMonitor:
    def __init__(self, ig):
        self.count = 0
        self.start = time.time()
        ig.on(EventType.REQUEST, self.tick)

    def tick(self, event):
        self.count += 1
        if self.count % 100 == 0:
            elapsed = time.time() - self.start
            print(f"100 requests in {elapsed:.2f}s (last: {event.endpoint})")
            self.start = time.time()

ig = Instagram.anonymous(unlimited=True)
monitor = SpeedMonitor(ig)
```

### Removing Hooks

```python
ig.off(EventType.REQUEST, monitor.tick)
```
