from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import (
    MissingParameterError,
    MissingKeyBuilderError,
    InvalidKeyBuilder,
    MissingCacheBackendError,
    InvalidCacheBackendError,
)
from rate_limiter.backend.token_bucket_cache import TokenBucketCacheBackend
from rate_limiter.backend.redis_token_bucket_cache import RedisTokenBucketCacheBackend
from rate_limiter.key_builder.base import KeyBuilder
from django.http import JsonResponse


class TokenBucketRateLimiter:

    def __init__(self, get_response):
        self.next_chain_middleware = get_response

        algorithm = rl_settings.algorithm
        bucket_size = rl_settings.bucket_size
        refill_rate = rl_settings.refill_rate

        required_params = {
            "algorithm": algorithm,
            "bucket_size": bucket_size,
            "refill_rate": refill_rate,
        }

        missing_params = [
            name for name, value in required_params.items() if value is None
        ]
        provided_params = [
            name for name, value in required_params.items() if value is not None
        ]

        if missing_params:
            raise MissingParameterError(
                algorithm_name=algorithm or "<unknown>",
                provided_params=provided_params,
                missing_params=missing_params,
            )

        backend = rl_settings.backend
        if not backend:
            raise MissingCacheBackendError("Cache backend must be provided")
        if ("cache" not in backend) or ("cache_alias" not in backend):
            raise InvalidCacheBackendError("cache and cache_alias must be provided")

        self.backend = (
            RedisTokenBucketCacheBackend(
                bucket_size=bucket_size,
                refill_rate=refill_rate,
                cache_alias=backend["cache_alias"],
            )
            if backend["cache"] == "redis"
            else TokenBucketCacheBackend(
                bucket_size=bucket_size,
                refill_rate=refill_rate,
            )
        )

        key_builder = rl_settings.key_builder
        if not key_builder:
            raise MissingKeyBuilderError("Key builder must be passed")
        if not isinstance(key_builder, KeyBuilder):
            raise InvalidKeyBuilder("key builder must be an instance of key builder")
        self.key_builder = key_builder

    def __call__(self, request):
        key = self.key_builder.build(request)

        allow = self.backend.allow(key)
        if not allow:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)
        return self.next_chain_middleware(request)
