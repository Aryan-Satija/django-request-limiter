from django_redis import get_redis_connection
from rate_limiter.backend.base import BaseBackend


LUA_SCRIPT = """
local current = redis.call("GET", KEYS[1])

if not current then
    redis.call("SET", KEYS[1], 1, "EX", ARGV[1])
    return 1
end

current = tonumber(current)

if current + 1 > tonumber(ARGV[2]) then
    return 0
end

redis.call("INCR", KEYS[1])
return 1
"""


class RedisCacheBackend(BaseBackend):

    def __init__(self, window: int, threshold: int, cache_alias: str):
        self.window = window
        self.threshold = threshold
        self.redis = get_redis_connection(cache_alias)
        self.simple_cache_atomic_script = self.redis.register_script(LUA_SCRIPT)

    def allow(self, key: str) -> bool:
        result = self.simple_cache_atomic_script(
            keys=[key],
            args=[self.window, self.threshold]
        )
        return bool(result)
