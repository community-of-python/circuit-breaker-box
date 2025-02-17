import typing


class BaseCircuitBreakerError(Exception):
    def __init__(self, *args: typing.Any) -> None:  # noqa: ANN401
        super().__init__(*args)


class HostUnavailableError(BaseCircuitBreakerError):
    pass


class RetryFlowError(BaseCircuitBreakerError):
    """Error should never happen. If it happens, it means that the retry flow is not correct."""
