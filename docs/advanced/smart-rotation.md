# Smart Rotation

`SmartRotationCoordinator` coordinates **proxy selection**, **browser identity (AntiDetect)**, and **TLS session impersonation** across every HTTP request attempt inside `HttpClient` and `AsyncHttpClient`.

## How It Works

```text
HttpClient / AsyncHttpClient
    └── SmartRotationCoordinator
          ├── AntiDetect   -> Chrome 142 / 136 profile selection
          ├── ProxyManager -> Weighted proxy selection + scoring
          └── TLS Session  -> curl_cffi browser impersonation
```

For authenticated requests with a fingerprinted session (`SessionInfo.fingerprint`), identity stays **locked** to the session's browser profile so headers never drift inconsistently mid-session, while proxies and error actions are still coordinated cleanly.

## Coordinator API

```python
from instaharvest_v2.anti_detect import AntiDetect
from instaharvest_v2.proxy_manager import ProxyManager
from instaharvest_v2.smart_rotation import SmartRotationCoordinator

anti_detect = AntiDetect()
proxy_mgr = ProxyManager()
proxy_mgr.add_proxy("http://user:pass@proxy.example.com:8080")

coord = SmartRotationCoordinator(anti_detect, proxy_mgr)

# Lifecycle hooks called around HTTP attempts:
ctx = coord.on_request_start("GET", "/api/v1/users/123/info/", attempt=1, max_attempts=4)
coord.on_request_success(ctx, status_code=200, elapsed_ms=145.0)

# Summary & stats
print(coord.get_summary_line())
print(coord.get_stats())
```

## Error → Action Matrix

| Error / Status | Coordinator Action |
|---|---|
| `429 RateLimitError` | Rotate proxy/identity/TLS (unlocked sessions), pause & escalate |
| `ChallengeRequired` / `CheckpointRequired` | Rotate identity + TLS, attempt handler resolution |
| `NetworkError` | Rotate proxy + TLS, keep identity |
| `LoginRequired` | Keep proxy, refresh or rotate session |
| `NotFoundError` / `PrivateAccountError` | No rotation (valid API response) |
| 3+ consecutive proxy failures | Temporarily blacklist proxy (`is_proxy_blacklisted()`) |
