from typing import Sequence


class MissingParameterError(ValueError):
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
