import time
from django.core.cache import cache
from .base import BaseBackend

class LeakyBucketBackend(BaseBackend):
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate

    def allow(self, key: str) -> bool:
        now = time.time()
        data = cache.get(key)

        if not data:
            cache.set(key, (1, now))
            return True

        level, last = data

        level = max(0, level - (now - last) * self.leak_rate)

        if level >= self.capacity:
            cache.set(key, (level, now))
            return False

        cache.set(key, (level + 1, now))
        return True
