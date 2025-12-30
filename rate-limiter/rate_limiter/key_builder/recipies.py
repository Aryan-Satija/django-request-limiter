from rate_limiter.key_builder.base import KeyBuilder
from django.http import HttpRequest


class IpPathKeyBuilder(KeyBuilder):
    def build(self, request: HttpRequest) -> str:
        ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"ip:{ip}:path:{request.path}"


class IpOnlyKeyBuilder(KeyBuilder):
    def build(self, request: HttpRequest) -> str:
        ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"ip:{ip}"


class MethodGlobalKeyBuilder(KeyBuilder):
    def build(self, request: HttpRequest) -> str:
        return f"method:{request.method}"


class GlobalKeyBuilder(KeyBuilder):
    def build(self, request: HttpRequest) -> str:
        return "global"
