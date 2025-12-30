from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import MissingParameterError, MissingKeyBuilderError, InvalidKeyBuilder
from rate_limiter.backend.leaky_bucket_cache import LeakyBucketBackend
from rate_limiter.key_builder.base import KeyBuilder
from django.http import JsonResponse


class LeakyBucketRateLimiter:

    def __init__(self, get_response):
        self.next_chain_middleware = get_response

        algorithm = rl_settings.algorithm
        capacity = rl_settings.capacity
        leak_rate = rl_settings.leak_rate

        required_params = {
            "algorithm": algorithm,
            "capacity": capacity,
            "leak_rate": leak_rate,
        }

        missing_params = [name for name, value in required_params.items() if value is None]
        provided_params = [name for name, value in required_params.items() if value is not None]

        if missing_params:
            raise MissingParameterError(
                algorithm_name=algorithm or "<unknown>",
                provided_params=provided_params,
                missing_params=missing_params,
            )

        self.backend = LeakyBucketBackend(capacity, leak_rate)
        key_builder = rl_settings.key_builder
        if not key_builder:
            raise MissingKeyBuilderError('Key builder must be passed')
        if not isinstance(key_builder, KeyBuilder):
            raise InvalidKeyBuilder('key builder must be an instance of key builder')
        self.key_builder = key_builder

    def __call__(self, request):
        key = self.key_builder.build(request)

        allow = self.backend.allow(key)
        if not allow:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)
        return self.next_chain_middleware(request)
