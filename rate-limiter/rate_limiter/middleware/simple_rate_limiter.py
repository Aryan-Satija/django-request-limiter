from django.http import HttpRequest, JsonResponse
from rate_limiter.conf import rl_settings
from rate_limiter.backend.simple_cache import CacheBackend
from rate_limiter.exceptions import MissingParameterError


class RateLimiterMiddleware:

    def __init__(self, get_response):
        self.next_chain_middleware = get_response

        algorithm = rl_settings.algorithm
        window = rl_settings.window
        threshold = rl_settings.threshold

        required_params = {
            "algorithm": algorithm,
            "window": window,
            "threshold": threshold,
        }

        missing_params = [name for name, value in required_params.items() if value is None]
        provided_params = [name for name, value in required_params.items() if value is not None]

        if missing_params:
            raise MissingParameterError(
                algorithm_name=algorithm or "<unknown>",
                provided_params=provided_params,
                missing_params=missing_params,
            )

        self.backend = CacheBackend(window=window, threshold=threshold)


    def __call__(self, request: HttpRequest):
        ip_address = request.META.get("REMOTE_ADDR")
        key = f"fl:{ip_address}:{request.path}"

        allow = self.backend.allow(key)
        if not allow:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)
        return self.next_chain_middleware(request)
