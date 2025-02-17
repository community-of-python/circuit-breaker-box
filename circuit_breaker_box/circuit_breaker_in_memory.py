import dataclasses
import logging
import typing

from cachetools import TTLCache

from circuit_breaker_box import BaseCircuitBreaker, errors
from circuit_breaker_box.circuit_breaker_base import RequestType, ResponseType


logger = logging.getLogger(__name__)


@dataclasses.dataclass(kw_only=True, slots=True)
class CircuitBreakerInMemory(BaseCircuitBreaker[RequestType, ResponseType]):
    max_cache_size: int
    cache_hosts_with_errors: TTLCache[typing.Any, typing.Any] = dataclasses.field(init=False)
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.cache_hosts_with_errors: TTLCache[typing.Any, typing.Any] = TTLCache(
            maxsize=self.max_cache_size, ttl=self.reset_timeout_in_seconds
        )

    async def increment_failures_count(self, host: str) -> None:
        if host in self.cache_hosts_with_errors:
            self.cache_hosts_with_errors[host] = self.cache_hosts_with_errors[host] + 1
            logger.debug("Incremented error for host: '%s', errors: %s", host, self.cache_hosts_with_errors[host])
        else:
            self.cache_hosts_with_errors[host] = 1
            logger.debug("Added host: %s, errors: %s", host, self.cache_hosts_with_errors[host])

    async def is_host_available(self, host: str) -> bool:
        failures_count: typing.Final = int(self.cache_hosts_with_errors.get(host) or 0)
        is_available: bool = failures_count <= self.max_failure_count
        logger.debug(
            "host: '%s', failures_count: '%s', self.max_failure_count: '%s', is_available: '%s'",
            host,
            failures_count,
            self.max_failure_count,
            is_available,
        )
        return is_available

    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        msg = f"Host {host} is unavailable"
        raise errors.HostUnavailableError(msg)
