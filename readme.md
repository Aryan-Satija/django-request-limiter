# Django Redis Rate Limiter

A **production‑grade, Redis‑backed rate limiter for Django**, designed from first principles.  
It supports **multiple algorithms**, **atomic Redis operations via Lua**, **flexible key composition**, and a **clean, extensible architecture** suitable for real systems.

This document explains **what we built, why each piece exists, and how it works internally**.

---

## 1. What problem are we solving?

A rate limiter protects your backend from:
- API abuse
- DDoS‑like traffic spikes
- Accidental infinite client retries

A correct rate limiter must:
1. Be **correct under concurrency**
2. Be **fast (O(1))** per request
3. Work **across multiple processes / servers**

Django’s in‑memory cache **cannot guarantee atomicity across workers**.  
Redis **can**, especially when combined with **Lua scripts**.

That is why this project is **Redis‑first**.

---

## 2. High‑level Architecture

```
request
   ↓
Middleware
   ↓
Policy Resolver (optional)
   ↓
Key Builder (optional)
   ↓
Algorithm resolver (leaky-bucket, token-bucket, etc)
   ↓            
Backend (Redis/localMem) 
   ↓
ALLOW / BLOCK
```

Each block has **one responsibility**.

---

## 3. Folder Structure

```
rate-limiter/
├── __init__.py
├── apps.py
├── conf.py
├── algorithm_registry.py
├── middleware.py
├── exceptions.py
├── policy/
│   ├── __init__.py
│   ├── resolver.py
│   └── policies.py
├── key_builder/
│   ├── __init__.py
│   |── base.py
|   |── recipes.py
│   └── schema.py
├── backend/
│   ├── __init__.py
│   ├── base.py
│   ├── simple_cache.py
│   ├── token_bucket_cache.py
│   ├── leaky_bucket_cache.py
│   ├── redis_simple_cache.py
│   ├── redis_token_bucket_cache.py
│   └── redis_leaky_bucket_cache.py
```
---

## 4. App Initialization (apps.py)

```python
from django.apps import AppConfig

class RateLimiterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rate_limiter"
```

When added to `INSTALLED_APPS`, Django:
- Registers the app
- Resolves imports correctly
- Allows signals / configs later

---

## 5. Policy System

### What a policy actually is

A policy is a **named, fully-configured rate-limiting rule** that defines:
- which algorithm to use
- how that algorithm is parameterized
- how the rate-limit key may be constructed, etc

Multiple policies can coexist, and **one policy is selected per request at runtime**.

---

### Why policies exist

Different classes of requests require different limits:
- free vs paid users
- public vs internal APIs
- login vs read vs write endpoints

A single global rule is insufficient for real systems.

So we separate:
- **policy definitions** → what rules exist
- **policy resolution** → which rule applies to this request

---

### Configuration-driven design

Policies are defined declaratively using a configuration object:

```python
RATE_LIMITER_CONFIGURATION = {
    'policies': {
        'free': {
            'algorithm': 'simple',
            'window': 300,
            'threshold': 5,
            'key_builder': SchemaKeyBuilder(ip=True)
        },
        'paid': {
            'algorithm': 'token-bucket',
            'bucket_size': 5,
            'refill_rate': 0.2
        }
    },
    'policy_resolver': lambda request: request.GET.get('plan', 'free'),
    'algorithm': 'composite'
}
```

---

## 6. Key Builder (most important design)

### Why keys matter

Rate limiting is **not about counting requests**.  
It is about **counting requests per identity**.

That identity is defined entirely by the **rate-limit key**.

Bad key → wrong identity → wrong limits.

Everything else (algorithm, Redis, Lua) is secondary.

---

### What a key builder really does

A key builder answers exactly one question:

“When should two requests share the same rate-limit counter?”

Possible dimensions include:
- IP address
- request path
- HTTP method
- headers
- query parameters
- arbitrary user-defined logic

The chosen dimensions determine **who competes with whom** for a limit.

---

### Key builder recipes

We also provide **explicit key-builder recipes**.
Each recipe encodes a clear and predictable behavior.

---

### 1. IpOnlyKeyBuilder

Key format:

    fl:ip=1.2.3.4

All requests from the same IP share a single counter.

Ignores:
- path
- method
- endpoint type

Use cases:
- brute-force protection
- coarse IP-level throttling
- infrastructure safety limits

---

### 2. IpPathKeyBuilder

Key format:

    fl:ip=1.2.3.4:path=/login

Requests are grouped by:
- IP
- endpoint path

Different endpoints get **independent limits**.

Use cases:
- strict limits on /login
- lenient limits on /search
- endpoint-level isolation

---

### 3. MethodGlobalKeyBuilder

Key format:

    fl:method=POST

All requests of the same HTTP method share a counter globally.

Use cases:
- throttling expensive POST/PUT operations
- protecting write-heavy APIs

---

### 4. GlobalKeyBuilder

Key format:

    fl:global

All requests share the same counter.

Use cases:
- global throughput caps
- circuit-breaker-style protection
- downstream dependency safety

---

### Same limits, different behavior (critical example)

Assume:

    threshold = 5
    window    = 300 seconds (5 minutes)

We compare two key builders with **identical limits**.

---

### Case 1: IpPathKeyBuilder

Key format:

    fl:ip=<IP>:path=<PATH>

Requests from IP 1.2.3.4:

    POST /login   -> counter A
    POST /login   -> counter A
    POST /login   -> counter A
    POST /login   -> counter A
    POST /login   -> counter A   ALLOWED (5/5)

    POST /search  -> counter B   ALLOWED (1/5)

Result:
- 5 requests per IP **per endpoint**
- exhausting /login does not affect /search

---

### Case 2: IpOnlyKeyBuilder

Key format:

    fl:ip=<IP>

Same request pattern:

    POST /login   -> counter X
    POST /login   -> counter X
    POST /login   -> counter X
    POST /login   -> counter X
    POST /login   -> counter X   ALLOWED (5/5)

    POST /search  -> counter X   BLOCKED

Result:
- all endpoints share a single bucket
- one hot endpoint blocks the entire IP

---

## 7. Backend Interface

### BaseBackend

```python
from abc import ABC, abstractmethod

class BaseBackend(ABC):
    @abstractmethod
    def allow(self, key: str) -> bool:
        pass
```

Why an interface?
- Swap Redis / Cache / Memory
- Test independently
- Enforce consistency

---

## 8. Redis Backend (Atomic Core)

### Why Redis?
- Shared across workers
- Extremely fast
- Supports **Lua scripting**

### Why Lua?

Without Lua:
```
GET key
IF < limit
  INCR key
```

**Race condition** under concurrency.

With Lua:
- Entire logic runs **atomically on Redis server**
- No interleaving

---

## 9. Simple Fixed Window (Lua)

```lua
local current = redis.call("GET", KEYS[1])

if not current then
    redis.call("SET", KEYS[1], 1, "EX", ARGV[1])
    return 1
end

current = tonumber(current)

if current < tonumber(ARGV[2]) then
    redis.call("INCR", KEYS[1])
    return 1
end

return 0
```

### What this guarantees
- Correct count
- Correct expiry
- No race conditions

---

## 10. Fixed Window, Token Bucket & Leaky Bucket

Supported backends:
- **Fixed Window** → deterministic expiration

```python
RATE_LIMITER_CONFIGURATION={
    'algorithm': 'simple',
    'window': 60,
    'threshold': 100,
    ...
}
```

- **Token Bucket** → smooth bursts

```python
RATE_LIMITER_CONFIGURATION={
    'algorithm': 'token-bucket',
    'bucket_size': 20,
    'refill_rate': 5,
    ...
}
```

- **Leaky Bucket** → constant outflow

```python
RATE_LIMITER_CONFIGURATION={
    'algorithm': 'leaky-bucket',
    'capacity': 20,
    'leak_rate': 5,
    ...
}
```

Each algorithm:
- Encapsulates its own math
- Uses LocalMem/Redis for shared state
- Respects atomicity

They all conform to `BaseBackend`.

---

## 11. Middleware Flow (High level overview)

```python
class RateLimitMiddleware:
    def __call__(self, request):
        key = build_key(request)
        allowed = backend.allow(key, policy)

        if not allowed:
            return JsonResponse({"detail": "Rate limit exceeded"}, status=429)

        return self.get_response(request)
```

This keeps:
- Request logic clean
- Enforcement centralized

---

## 12. Decorator Support (To Be Done)

```python
@rate_limit(policy="login")
def login_view(request):
    ...
```

Use decorators when:
- Limiting specific endpoints
- Avoiding global middleware

---

## 13. Exceptions Hierarchy

Exceptions are deliberately split into **configuration-time errors** and **runtime errors**.

This distinction is fundamental.

---

### Configuration Errors (fail fast at startup)

These indicate **developer misconfiguration** and should surface immediately.

```text
Exception
└── RateLimiterConfigurationError
    ├── MissingAlgorithmError
    ├── InvalidAlgorithmError
    └── MissingParameterError

Exception
└── KeyBuilderConfigurationError
    ├── MissingKeyBuilderError
    └── InvalidKeyBuilder

Exception
└── CacheBackendConfigurationError
    ├── MissingCacheBackendError
    └── InvalidCacheBackendError
```

Why this matters:
- Debuggable failures
- Safe defaults
- No silent bypasses

---

## 14. Settings Integration

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

Redis is accessed via:
```python
from django_redis import get_redis_connection
```

---

## 15. Design Principles Used

- **Single Responsibility**
- **Explicit over implicit**
- **Fail fast** on misconfiguration
- **Atomic correctness > convenience**
- **Interfaces over concrete classes**

This is why the system scales conceptually.

---

## 16. Default Configuration

The rate limiter is designed to be **safe by default**.

If the user provides no configuration—or only a partial one—the system falls back to a **sensible default configuration** that works out of the box.

---

### Default configuration definition

```python
DEFAULT_CONFIGURATION = {
    "window": 60,
    "threshold": 100,
    "algorithm": "simple-rate-limiter",
    "key_builder": IpPathKeyBuilder(),
    "backend": {
        "cache": "django-default",
        "cache_alias": "default"
    }
}
```

---

**Built with intent, not magic.**
