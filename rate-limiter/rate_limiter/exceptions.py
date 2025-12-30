from typing import Sequence


class RateLimiterConfigurationError(Exception):
    pass


class MissingParameterError(RateLimiterConfigurationError):
    """Raised when required parameters for an algorithm are missing."""

    def __init__(
        self,
        algorithm_name: str,
        provided_params: Sequence[str],
        missing_params: Sequence[str],
    ) -> None:
        self.algorithm_name = algorithm_name
        self.provided_params = tuple(provided_params)
        self.missing_params = tuple(missing_params)

        message = (
            f"Algorithm: {algorithm_name}\n"
            f"Provided parameters: {', '.join(self.provided_params)}\n"
            f"Missing parameters: {', '.join(self.missing_params)}"
        )

        super().__init__(message)


class MissingAlgorithmError(RateLimiterConfigurationError):
    """Raised when the algorithm itself is missing"""

    pass


class InvalidAlgorithmError(RateLimiterConfigurationError):
    """Raised when the algorithm name is invalid"""

    def __init__(self, passed_algorithm_name: str):
        super().__init__(f'Invalid algorithm name passed: {passed_algorithm_name}')


class RateLimiterRuntimeError(Exception):
    """
    Errors that occur while processing a request.
    """
    pass


class PolicyResolutionError(RateLimiterRuntimeError):
    """
    Raised when policy_resolver:
    - raises an exception
    - returns an invalid type
    """
    pass


class UnknownPolicyError(RateLimiterRuntimeError):
    def __init__(self, policy_name: str):
        super().__init__(f"Unknown policy '{policy_name}'")
        

class KeyBuilderConfigurationError(Exception):
    pass


class MissingKeyBuilderError(KeyBuilderConfigurationError):
    pass


class InvalidKeyBuilder(KeyBuilderConfigurationError):
    pass
