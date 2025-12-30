import inspect
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from rate_limiter.algorithm_registry import ALGORITHM_REGISTRY
from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import (
    MissingAlgorithmError,
    InvalidAlgorithmError,
    MissingParameterError,
    UnknownPolicyError,
    PolicyResolutionError,
)


class CompositeRateLimiter:

    def __init__(self, get_response):
        self.get_response = get_response

        algorithm = rl_settings.algorithm
        policies = rl_settings.policies
        policy_resolver = rl_settings.policy_resolver

        # -------------------------
        # Required settings
        # -------------------------
        if algorithm is None or policies is None or policy_resolver is None:
            raise ImproperlyConfigured(
                "algorithm, policies, and policy_resolver must be provided"
            )

        # -------------------------
        # policy_resolver validation
        # -------------------------
        if not callable(policy_resolver):
            raise ImproperlyConfigured("policy_resolver must be callable")

        sig = inspect.signature(policy_resolver)
        if len(sig.parameters) != 1:
            raise ImproperlyConfigured(
                "policy_resolver must accept exactly one argument (HttpRequest)"
            )

        # -------------------------
        # policies validation (eager)
        # -------------------------
        if not isinstance(policies, dict):
            raise ImproperlyConfigured("policies must be a dict")

        for name, policy in policies.items():
            if not isinstance(name, str):
                raise ImproperlyConfigured("policy names must be strings")

            if not isinstance(policy, dict):
                raise ImproperlyConfigured(f"policy '{name}' must be a dict")

            algo = policy.get("algorithm")
            if not algo:
                raise MissingAlgorithmError(f"policy '{name}' has no algorithm")

            if algo not in ALGORITHM_REGISTRY:
                raise InvalidAlgorithmError(algo)

            required = ALGORITHM_REGISTRY[algo]["required_params"]
            missing = required - policy.keys()
            if missing:
                raise MissingParameterError(
                    algorithm_name=algo,
                    missing_params=list(missing),
                )

        self.policy_resolver = policy_resolver
        self.policies = policies

        self.backends = {
            name: ALGORITHM_REGISTRY[policy["algorithm"]]["backend"](
                **{k: policy[k] for k in ALGORITHM_REGISTRY[policy["algorithm"]]["required_params"]}
            )
            for name, policy in policies.items()
        }

    def __call__(self, request):
        try:
            policy_name = self.policy_resolver(request)
        except Exception as exc:
            raise PolicyResolutionError(
                "policy_resolver raised an exception"
            ) from exc

        if not isinstance(policy_name, str):
            raise PolicyResolutionError(
                f"policy_resolver must return str, got {type(policy_name).__name__}"
            )

        if policy_name not in self.policies:
            raise UnknownPolicyError(policy_name)

        backend = self.backends[policy_name]

        ip = request.META.get("REMOTE_ADDR", "unknown")
        key = f"rl:{policy_name}:{ip}:{request.path}"

        allow = backend.allow(key)

        if not allow:
            return JsonResponse(
                {"detail": "rate limit exceeded"},
                status=429,
            )

        return self.get_response(request)
