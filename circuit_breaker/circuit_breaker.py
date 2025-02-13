import abc
import dataclasses
import typing

import tenacity
from cachetools import TTLCache
from loguru import logger
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import WatchError

from circuit_breaker import errors


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


def _log_attempt(retry_state: tenacity.RetryCallState) -> None:
    logger.info(f"Attempt redis_reconnect: {retry_state=}")


@dataclasses.dataclass(kw_only=True, slots=True)
class CircuitBreakerRedis(BaseCircuitBreaker):
    redis_connection: "aioredis.Redis[str]"

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential_jitter(),
        retry=tenacity.retry_if_exception_type((WatchError, RedisConnectionError, ConnectionResetError, TimeoutError)),
        reraise=True,
        before=_log_attempt,
    )
    async def increment_failures_count(self, host: str) -> None:
        redis_key: typing.Final = f"circuit-breaker-{host}"
        increment_result: int = await self.redis_connection.incr(redis_key)
        logger.debug(f"Incremented error for {redis_key=} {increment_result=}")
        is_expire_set: bool = await self.redis_connection.expire(redis_key, self.reset_timeout_in_seconds)
        logger.debug(f"Expire set for {redis_key=} {is_expire_set=}")

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential_jitter(),
        retry=tenacity.retry_if_exception_type((WatchError, RedisConnectionError, ConnectionResetError, TimeoutError)),
        reraise=True,
        before=_log_attempt,
    )
    async def is_host_available(self, host: str) -> bool:
        failures_count: typing.Final = int(await self.redis_connection.get(f"circuit-breaker-{host}") or 0)
        is_available: bool = failures_count <= self.max_failure_count
        logger.debug(f"Host: {host} {failures_count=} {self.max_failure_count=} {is_available=}")
        return is_available

    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        msg = f"Host {host} is unavailable"
        raise errors.HostUnavailableError(msg)


@dataclasses.dataclass(kw_only=True, slots=True)
class CircuitBreakerInMemory(BaseCircuitBreaker):
    max_cache_size: int
    cache_hosts_with_errors: TTLCache[typing.Any, typing.Any] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.cache_hosts_with_errors: TTLCache[typing.Any, typing.Any] = TTLCache(
            maxsize=self.max_cache_size, ttl=self.reset_timeout_in_seconds
        )

    async def increment_failures_count(self, host: str) -> None:
        if host in self.cache_hosts_with_errors:
            self.cache_hosts_with_errors[host] = self.cache_hosts_with_errors[host] + 1
            logger.debug(f"Incremented error for {host=} {self.cache_hosts_with_errors[host]=}")
        else:
            self.cache_hosts_with_errors[host] = 1
            logger.debug(f"Added host {host=} {self.cache_hosts_with_errors[host]=}")

    async def is_host_available(self, host: str) -> bool:
        failures_count: typing.Final = int(self.cache_hosts_with_errors.get(host) or 0)
        is_available: bool = failures_count <= self.max_failure_count
        logger.debug(f"{host=} {failures_count=} {self.max_failure_count=} {is_available=}")
        return is_available

    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        msg = f"Host {host} is unavailable"
        raise errors.HostUnavailableError(msg)
