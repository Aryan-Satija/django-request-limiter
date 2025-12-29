from django.conf import settings

DEFAULT_CONFIGURATION = {
    "window": 60,
    "threshold": 100,
    "algorithm": "simple-rate-limiter",
}

USER_SETTINGS = getattr(settings, "RATE_LIMITER_CONFIGURATION", {})


class RateLimiterSettings:
    def __getattr__(self, key: str):
        if key in USER_SETTINGS:
            return USER_SETTINGS[key]
        return DEFAULT_CONFIGURATION.get(key, None)


rl_settings = RateLimiterSettings()
