from django.core.cache import cache
from rate_limiter.backend.base import BaseBackend


class CacheBackend(BaseBackend):

    def __init__(self, window: int, threshold: int):
        self.window = window
        self.threshold = threshold

    def allow(self, key: str) -> bool:
        value = cache.get(key, 0)

        if value == 0:
            cache.set(key, value + 1, timeout=self.window)
            return True

        cache.incr(key)

        if value + 1 > self.threshold:
            return False

        return True