from rate_limiter.key_builder.base import KeyBuilder
from django.http import HttpRequest


class SchemaKeyBuilder(KeyBuilder):
    def __init__(
        self,
        ip: bool = False,
        path: bool = False,
        method: bool = False,
        header: str | None = None,
        params: list[str] | None = None,
        callable_part=None,
        prefix: str = "rl",
    ):
        self.ip = ip
        self.path = path
        self.method = method
        self.header = header
        self.params = params or []
        self.callable_part = callable_part
        self.prefix = prefix

    def build(self, request: HttpRequest) -> str:
        parts = [self.prefix]

        if self.ip:
            parts.append(f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}")

        if self.path:
            parts.append(f"path:{request.path}")

        if self.method:
            parts.append(f"method:{request.method}")

        if self.header:
            value = request.headers.get(self.header)
            if value:
                parts.append(f"header:{self.header}={value}")

        for param in self.params:
            value = request.GET.get(param)
            if value is not None:
                parts.append(f"param:{param}={value}")

        if self.callable_part:
            value = self.callable_part(request)
            if not isinstance(value, str):
                raise TypeError("callable_part must return str")
            parts.append(value)

        return ":".join(parts)
