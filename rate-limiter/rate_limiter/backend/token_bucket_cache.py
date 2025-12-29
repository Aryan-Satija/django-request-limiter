import math
import time
from typing import Tuple

from django.core.cache import cache

from rate_limiter.backend.base import BaseBackend


class TokenBucketCacheBackend(BaseBackend):
    """
    Token Bucket rate limiter using Django cache.
    """

    def __init__(self, bucket_size: int, refill_rate: float, ttl: int = 3600):
        self.bucket_size = bucket_size
        self.refill_rate = refill_rate
        self.ttl = ttl

    def allow(self, key: str) -> bool:
        now = time.time()
        tokens, last_refill = self._get_bucket(key, now)

        elapsed = now - last_refill
        tokens = min(
            self.bucket_size,
            tokens + int(math.floor(elapsed * self.refill_rate)),
        )

        if tokens == 0:
            return False

        tokens -= 1
        self._save_bucket(key, tokens, now)
        return True

    def _get_bucket(self, key: str, now: float) -> Tuple[int, float]:
        data = cache.get(key)
        if data is None:
            return self.bucket_size, now
        return data

    def _save_bucket(self, key: str, tokens: int, now: float) -> None:
        cache.set(key, (tokens, now), timeout=self.ttl)
