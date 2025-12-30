from rate_limiter.backend.simple_cache import CacheBackend
from rate_limiter.backend.leaky_bucket_cache import LeakyBucketBackend
from rate_limiter.backend.token_bucket_cache import TokenBucketCacheBackend


ALGORITHM_REGISTRY = {
    "simple": {
        "backend": CacheBackend,
        "required_params": {"window", "threshold"},
    },
    "token-bucket": {
        "backend": TokenBucketCacheBackend,
        "required_params": {"bucket_size", "refill_rate"},
    },
    "leaky-bucket": {
        "backend": LeakyBucketBackend,
        "required_params": {"capacity", "leak_rate"},
    },
}