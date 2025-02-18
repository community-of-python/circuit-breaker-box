import dataclasses
import logging
import typing

import tenacity
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import WatchError

from circuit_breaker_box import BaseCircuitBreaker, errors


logger = logging.getLogger(__name__)


def _log_attempt(retry_state: tenacity.RetryCallState) -> None:
    logger.info("Attempt redis_reconnect: %s", retry_state)


@dataclasses.dataclass(kw_only=True)
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
        logger.debug("Incremented error for redis_key: %s, increment_result: %s", redis_key, increment_result)
        is_expire_set: bool = await self.redis_connection.expire(redis_key, self.reset_timeout_in_seconds)
        logger.debug("Expire set for redis_key: %s, is_expire_set: %s", redis_key, is_expire_set)

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
