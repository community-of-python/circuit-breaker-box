import dataclasses
import logging
import typing

import httpx
import pytest
from redis import asyncio as aioredis

from circuit_breaker_box import CircuitBreakerInMemory, CircuitBreakerRedis
from examples.example_circuit_breaker import CustomCircuitBreakerInMemory


logger = logging.getLogger(__name__)

MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


@dataclasses.dataclass
class TestRedisConnection(aioredis.Redis):  # type: ignore[type-arg]
    errors: int = 0

    async def incr(self, host: str | bytes, amount: int = 1) -> int:
        logger.debug("host: %s, amount: %d{amount}", host, amount)
        self.errors = self.errors + 1
        return amount + 1

    async def expire(self, *args: typing.Any, **kwargs: typing.Any) -> bool:  # noqa: ANN401
        logger.debug(args, kwargs)
        return True

    async def get(self, host: str | bytes) -> int:
        logger.debug("host: %s, errors: %s", host, self.errors)
        return self.errors


@pytest.fixture(name="test_circuit_breaker_in_memory")
def fixture_circuit_breaker_in_memory() -> CircuitBreakerInMemory[httpx.Request, httpx.Response]:
    return CircuitBreakerInMemory[httpx.Request, httpx.Response](
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=[ZeroDivisionError],
    )


@pytest.fixture(name="test_circuit_breaker_redis")
def fixture_circuit_breaker_redis() -> CircuitBreakerRedis[httpx.Request, httpx.Response]:
    return CircuitBreakerRedis[httpx.Request, httpx.Response](
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        redis_connection=TestRedisConnection(),
        max_retries=MAX_RETRIES,
        exceptions_to_retry=[Exception],
    )


@pytest.fixture(name="test_custom_circuit_breaker_in_memory")
def fixture_custom_circuit_breaker_in_memory() -> CustomCircuitBreakerInMemory[httpx.Request, httpx.Response]:
    return CustomCircuitBreakerInMemory[httpx.Request, httpx.Response](
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=[Exception],
    )
