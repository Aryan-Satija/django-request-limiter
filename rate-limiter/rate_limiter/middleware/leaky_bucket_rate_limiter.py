from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import MissingParameterError
from rate_limiter.backend.leaky_bucket_cache import LeakyBucketBackend
from django.http import JsonResponse


class RateLimiterMiddleware:

    def __init__(self, get_response):
        self.next_chain_middleware = get_response

        algorithm = rl_settings.algorithm
        capacity = rl_settings.capacity
        leak_rate = rl_settings.leak_rate

        required_params = {
            "algorithm": algorithm,
            "bucket_size": capacity,
            "refill_rate": leak_rate,
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


    def __call__(self, request):
        ip_address = request.META.get("REMOTE_ADDR")
        key = f"fl:{ip_address}:{request.path}"

        allow = self.backend.allow(key)
        if not allow:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)
        return self.next_chain_middleware(request)
