# Multi-Account

Running heavy workloads from a single account increases rate-limit and checkpoint exposure. `MultiAccountManager` manages a pool of `Instagram` sessions with rotation, cooldowns, and health checks.

## Quick Example

```python
from instaharvest_v2 import MultiAccountManager

manager = MultiAccountManager()
manager.add_account("account1.env")
manager.add_account("account2.env")

# Or register existing Instagram instances directly:
# manager.add_instance(ig_client, name="bot_3")

# Execute an action across all healthy accounts (round-robin rotation)
results = manager.round_robin(
    lambda ig: ig.users.get_by_username("cristiano")
)
for item in results:
    print(item["username"], item["success"])

# Pick a single account via random or least-used selection
ig = manager.random_pick()
ig_least = manager.least_used()
```

## Rotation & Execution Strategies

| Method | Behavior |
|---|---|
| `add_account(env_file, debug=False)` | Loads `.env` credentials via `Instagram.from_env()` into the pool |
| `add_instance(ig_instance, name="")` | Registers an already-constructed `Instagram` client |
| `round_robin(action, skip_errors=True)` | Runs `action(ig)` across available accounts in rotation |
| `random_pick()` | Returns a random healthy `Instagram` instance |
| `least_used()` | Returns the healthy instance with lowest `use_count` |
| `execute(action, strategy="round_robin", ...)` | Unified execution wrapper with cooldown on errors |
| `healthcheck()` | Verifies health across registered accounts |
| `close_all()` | Closes sessions across all managed instances |

## `SmartRotationCoordinator` vs `MultiAccountManager`

| Feature | `SmartRotationCoordinator` | `MultiAccountManager` |
|---|---|---|
| **Goal** | Coordinate proxy + browser identity + TLS per request | Manage multiple authenticated `.env` / `Instagram` accounts |
| **Granularity** | Per-HTTP attempt inside `HttpClient` / `AsyncHttpClient` | Account-level pool selection & error cooldowns |
| **Use Case** | Proxy scoring, identity locking, error matrix | Multi-account execution (`round_robin`, `least_used`, `healthcheck`) |

## Cleanup

```python
# Inspect account pool status
for info in manager.accounts:
    print(info["username"], info["is_healthy"], info["use_count"])

# Close all managed clients
manager.close_all()
```
