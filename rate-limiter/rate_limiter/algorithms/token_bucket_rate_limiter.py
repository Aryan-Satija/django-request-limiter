from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import MissingParameterError
from rate_limiter.backend.token_bucket_cache import TokenBucketCacheBackend
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

        missing_params = [name for name, value in required_params.items() if value is None]
        provided_params = [name for name, value in required_params.items() if value is not None]

        if missing_params:
            raise MissingParameterError(
                algorithm_name=algorithm or "<unknown>",
                provided_params=provided_params,
                missing_params=missing_params,
            )

        self.backend = TokenBucketCacheBackend(bucket_size, refill_rate)


    def __call__(self, request):
        ip_address = request.META.get("REMOTE_ADDR")
        key = f"fl:{ip_address}:{request.path}"

        allow = self.backend.allow(key)
        if not allow:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)
        return self.next_chain_middleware(request)
