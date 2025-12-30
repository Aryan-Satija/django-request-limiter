from django.conf import settings
from rate_limiter.key_builder.recipes import IpPathKeyBuilder

DEFAULT_CONFIGURATION = {
    "window": 60,
    "threshold": 100,
    "algorithm": "simple-rate-limiter",
    "key_builder": IpPathKeyBuilder()
}

USER_SETTINGS = getattr(settings, "RATE_LIMITER_CONFIGURATION", {})


class RateLimiterSettings:
    def __getattr__(self, key: str):
        if key in USER_SETTINGS:
            return USER_SETTINGS[key]
        return DEFAULT_CONFIGURATION.get(key, None)


rl_settings = RateLimiterSettings()
