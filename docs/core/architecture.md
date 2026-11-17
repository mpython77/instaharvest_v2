# Architecture

InstaHarvest v2 is built with a modular, layered architecture.

## System Overview

```mermaid
graph TB
    subgraph "User Layer"
        IG["Instagram / AsyncInstagram"]
    end
    
    subgraph "API Layer (Lazy-Loaded)"
        PUB["PublicAPI"]
        USR["UsersAPI"]
        MED["MediaAPI"]
        FD["FeedAPI"]
        ST["StoriesAPI"]
        DR["DirectAPI"]
        UP["UploadAPI"]
        MORE["...26 more sync / 27 async"]
    end

    subgraph "Core & Infrastructure"
        ANON["AnonClient"]
        HTTP["HttpClient"]
        SM["SessionManager"]
        RL["RateLimiter"]
        CB["CircuitBreaker / Metrics"]
        RC["ResponseCache"]
    end
    
    subgraph "Infrastructure"
        AD["AntiDetect"]
        PM["ProxyManager"]
        PH["ProxyHealth"]
        DF["DeviceFingerprint"]
        CH["ChallengeHandler"]
    end
    
    subgraph "Transport"
        CF["curl_cffi"]
    end
    
    IG --> PUB
    IG --> USR
    IG --> MED
    IG --> FD
    IG --> ST
    IG --> DR
    IG --> UP
    IG --> MORE
    
    PUB --> ANON
    USR --> HTTP
    MED --> HTTP
    FD --> HTTP
    ST --> HTTP
    DR --> HTTP
    UP --> HTTP
    
    ANON --> AD
    ANON --> PM
    HTTP --> SM
    HTTP --> RL
    HTTP --> AD
    HTTP --> PM
    HTTP --> CH
    
    AD --> DF
    PM --> PH
    
    ANON --> CF
    HTTP --> CF
```

## Module Map

| Module | File | Purpose |
|---|---|---|
| **Instagram** | `instagram.py` | Main sync class — lazy-loads all 33 API modules |
| **AsyncInstagram** | `async_instagram.py` | Main async class — lazy-loads all 34 modules + true async I/O |
| **AnonClient** | `anon_client.py` | Anonymous scraping — configurable fallback chain + `ResponseCache` |
| **AsyncAnonClient** | `async_anon_client.py` | Async anonymous scraping |
| **HttpClient** | `client.py` | Authenticated HTTP client + `CircuitBreaker` + metrics |
| **AsyncHttpClient** | `async_client.py` | Async authenticated HTTP + `CircuitBreaker` + metrics |
| **HttpUtils** | `http_utils.py` | Shared URL normalization, header builders, and `maybe_await()` |
| **LazyModules** | `_lazy_modules.py` | Lazy API module registry (`Instagram` + `AsyncInstagram`) |
| **Core** | `core/` | `CircuitBreaker`, `TokenBucketLimiter`, `ResponseCache`, `ConnectionPool`, `Metrics`, `StructuredLogger` |
| **SessionManager** | `session_manager.py` | Multi-session management |
| **ProxyManager** | `proxy_manager.py` | Proxy rotation + scoring |
| **AntiDetect** | `anti_detect.py` | TLS fingerprint + coherent Chrome headers |
| **RateLimiter** | `rate_limiter.py` | Thread-safe sliding window rate control |
| **SpeedModes** | `speed_modes.py` | SAFE/FAST/TURBO/UNLIMITED |
| **ChallengeHandler** | `challenge.py` | Email/SMS auto-verification |
| **DeviceFingerprint** | `device_fingerprint.py` | Mobile device simulation |
| **EventEmitter** | `events.py` | Event hooks system |
| **Plugin** | `plugin.py` | Plugin architecture |
| **Strategy** | `strategy.py` | Configurable strategy chain (`ProfileStrategy`, `PostsStrategy`) |

## Two Operation Modes

=== "Anonymous (No Login)"

    ```
    Instagram.anonymous()
        → PublicAPI
            → AnonClient
                → configurable strategies (no cookies needed)
                    → curl_cffi (TLS fingerprint)
    ```

=== "Authenticated (Login)"

    ```
    Instagram.from_env()
        → UsersAPI, MediaAPI, FeedAPI, ...
            → HttpClient
                → SessionManager (cookies)
                    → curl_cffi (TLS fingerprint)
    ```

## Design Patterns

| Pattern | Where | Why |
|---|---|---|
| **Strategy** | AnonClient | Configurable fallback strategies for resilience |
| **Chain of Responsibility** | Fallback chain | Auto-try next on failure |
| **Factory** | `Instagram.from_env()` | Clean initialization |
| **Observer** | EventEmitter | Decoupled event handling |
| **Proxy** | ProxyManager | Transparent proxy rotation |
| **Singleton** | Config | Shared configuration |
| **Builder** | StoryComposer | Fluent story creation |
