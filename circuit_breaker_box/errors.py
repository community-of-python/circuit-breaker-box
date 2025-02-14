import typing


class BaseCircuitBreakerError(Exception):
    def __init__(self, *args: typing.Any) -> None:  # noqa: ANN401
        super().__init__(*args)


class HostUnavailableError(BaseCircuitBreakerError):
    pass


class RetryFlowError(BaseCircuitBreakerError):
    pass
