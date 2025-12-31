import time
from django_redis import get_redis_connection
from rate_limiter.backend.base import BaseBackend


TOKEN_BUCKET_LUA = """
local data = redis.call("HMGET", KEYS[1], "tokens", "last_refill") -- Cleaner than calling GET twice!

local tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if not tokens or not last_refill then
    redis.call(
        "HMSET",
        KEYS[1],
        "tokens",
        ARGV[1] - 1,
        "last_refill",
        ARGV[3]
    ) -- Cleaner than calling SET twice!
    redis.call("EXPIRE", KEYS[1], ARGV[4])
    return 1
end

local elapsed = ARGV[3] - last_refill
local refill = math.floor(elapsed * ARGV[2])
tokens = math.min(tonumber(ARGV[1]), tokens + refill)

if tokens <= 0 then
    return 0
end

tokens = tokens - 1

redis.call(
    "HMSET",
    KEYS[1],
    "tokens",
    tokens,
    "last_refill",
    ARGV[3]
)
redis.call("EXPIRE", KEYS[1], ARGV[4])

return 1
"""


class RedisTokenBucketCacheBackend(BaseBackend):

    def __init__(
        self,
        bucket_size: int,
        refill_rate: float,
        cache_alias: str = "default",
        ttl: int = 3600,
    ):
        self.bucket_size = bucket_size
        self.refill_rate = refill_rate
        self.ttl = ttl

        self.redis = get_redis_connection(cache_alias)
        self.script = self.redis.register_script(TOKEN_BUCKET_LUA)

    def allow(self, key: str) -> bool:
        now = time.time()

        result = self.script(
            keys=[key],
            args=[
                self.bucket_size,
                self.refill_rate,
                now,
                self.ttl,
            ],
        )

        return bool(result)
