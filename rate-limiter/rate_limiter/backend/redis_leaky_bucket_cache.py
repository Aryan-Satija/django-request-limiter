import time
from django_redis import get_redis_connection
from rate_limiter.backend.base import BaseBackend


LEAKY_BUCKET_LUA = """
-- ARGV[1] = leak_rate (units per second)
-- ARGV[2] = capacity
-- ARGV[3] = current timestamp (now)
-- ARGV[4] = ttl

local now = ARGV[3]

-- Fetch current level and last timestamp
local data = redis.call("HMGET", KEYS[1], "levels", "last")

local levels = tonumber(data[1])
local last = tonumber(data[2])

-- First request / bucket does not exist
if not levels or not last then
    redis.call(
        "HMSET",
        KEYS[1],
        "levels",
        1,
        "last",
        now
    )
    redis.call("EXPIRE", KEYS[1], ARGV[4])
    return 1
end

-- Leak water over elapsed time
levels = math.max(0, levels - (now - last) * ARGV[1])

-- If bucket is full, reject
if levels >= tonumber(ARGV[2]) then
    redis.call(
        "HMSET",
        KEYS[1],
        "levels",
        levels,
        "last",
        now
    )
    redis.call("EXPIRE", KEYS[1], ARGV[4])
    return 0
end

-- Accept request, add water
redis.call(
    "HMSET",
    KEYS[1],
    "levels",
    levels + 1,
    "last",
    now
)
redis.call("EXPIRE", KEYS[1], ARGV[4])

return 1
"""


class RedisLeakyBucketCacheBackend(BaseBackend):
    """
    Redis-backed Leaky Bucket rate limiter using Lua for atomicity.
    """

    def __init__(
        self,
        capacity: int,
        leak_rate: float,
        cache_alias: str = "default",
        ttl: int = 3600,
    ):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.ttl = ttl

        self.redis = get_redis_connection(cache_alias)
        self.script = self.redis.register_script(LEAKY_BUCKET_LUA)

    def allow(self, key: str) -> bool:
        now = time.time()

        result = self.script(
            keys=[key],
            args=[
                self.leak_rate,
                self.capacity,
                now,
                self.ttl,
            ],
        )

        return bool(result)
