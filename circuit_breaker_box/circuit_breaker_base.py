import abc
import dataclasses
import typing


@dataclasses.dataclass(kw_only=True, slots=True)
class BaseCircuitBreaker:
    reset_timeout_in_seconds: int
    max_failure_count: int

    @abc.abstractmethod
    async def increment_failures_count(self, host: str) -> None: ...

    @abc.abstractmethod
    async def is_host_available(self, host: str) -> bool: ...

    @abc.abstractmethod
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn: ...
