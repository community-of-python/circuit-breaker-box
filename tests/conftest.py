import dataclasses
import typing

import pytest
from loguru import logger
from redis import asyncio as aioredis

from circuit_breaker.circuit_breaker import CircuitBreakerInMemory, CircuitBreakerRedis
from examples.example_circuit_breaker import CustomCircuitBreakerInMemory


HTTP_MAX_TRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


@dataclasses.dataclass
class TestRedisConnection(aioredis.Redis):  # type: ignore[type-arg]
    errors: int = 0

    async def incr(self, host: str | bytes, amount: int = 1) -> int:
        logger.debug(f"host: {host!s}, amount: {amount}")
        self.errors = self.errors + 1
        return amount + 1

    async def expire(self, *args: typing.Any, **kwargs: typing.Any) -> bool:  # noqa: ANN401
        logger.debug(f"{args=}, {kwargs=}")
        return True

    async def get(self, host: str | bytes) -> int:
        logger.debug(f"host: {host!s}, errors: {self.errors}")
        return self.errors


@pytest.fixture(name="test_circuit_breaker_in_memory")
def fixture_circuit_breaker_in_memory() -> CircuitBreakerInMemory:
    return CircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )


@pytest.fixture(name="test_circuit_breaker_redis")
def fixture_circuit_breaker_redis() -> CircuitBreakerRedis:
    return CircuitBreakerRedis(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        redis_connection=TestRedisConnection(),
    )


@pytest.fixture(name="test_custom_circuit_breaker_in_memory")
def fixture_custom_circuit_breaker_in_memory() -> CustomCircuitBreakerInMemory:
    return CustomCircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )
