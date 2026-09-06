import asyncio

import fastapi
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from circuit_breaker_box import CircuitBreakerInMemory, errors
from circuit_breaker_box.circuit_breaker_redis import CircuitBreakerRedis
from examples.example_retry_circuit_breaker import CustomCircuitBreakerInMemory
from tests.conftest import MAX_RETRIES, REDIS_MAX_RETRIES, SOME_HOST, FlakyRedisConnection


async def test_circuit_breaker_in_memory_cash(test_circuit_breaker_in_memory: CircuitBreakerInMemory) -> None:
    assert await test_circuit_breaker_in_memory.is_host_available(host=SOME_HOST)

    for _ in range(MAX_RETRIES):
        await test_circuit_breaker_in_memory.increment_failures_count(host=SOME_HOST)

    assert await test_circuit_breaker_in_memory.is_host_available(host=SOME_HOST) is False

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_in_memory.raise_host_unavailable_error(host=SOME_HOST)


async def test_circuit_breaker_with_redis(test_circuit_breaker_redis: CircuitBreakerRedis) -> None:
    assert await test_circuit_breaker_redis.is_host_available(host=SOME_HOST)

    for _ in range(MAX_RETRIES):
        await test_circuit_breaker_redis.increment_failures_count(host=SOME_HOST)

    assert await test_circuit_breaker_redis.is_host_available(host=SOME_HOST) is False

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_redis.raise_host_unavailable_error(host=SOME_HOST)


async def test_custom_circuit_breaker_in_memory_cash(
    test_custom_circuit_breaker_in_memory: CustomCircuitBreakerInMemory,
) -> None:
    assert await test_custom_circuit_breaker_in_memory.is_host_available(host=SOME_HOST)

    for _i in range(MAX_RETRIES):
        await test_custom_circuit_breaker_in_memory.increment_failures_count(host=SOME_HOST)

    assert await test_custom_circuit_breaker_in_memory.is_host_available(host=SOME_HOST) is False

    with pytest.raises(fastapi.HTTPException, match=f"Host: {SOME_HOST} is unavailable"):
        await test_custom_circuit_breaker_in_memory.raise_host_unavailable_error(host=SOME_HOST)


async def test_increment_failures_count_does_not_block_event_loop_while_waiting(
    test_circuit_breaker_flaky_redis: CircuitBreakerRedis,
    test_flaky_redis_connection: FlakyRedisConnection,
    test_short_redis_retry_wait: None,  # noqa: ARG001
) -> None:
    async def concurrent_coroutine() -> None:
        test_flaky_redis_connection.events.append("concurrent")

    await asyncio.gather(
        test_circuit_breaker_flaky_redis.increment_failures_count(host=SOME_HOST),
        concurrent_coroutine(),
    )

    assert test_flaky_redis_connection.events == ["attempt", "concurrent", "attempt"]


async def test_is_host_available_does_not_block_event_loop_while_waiting(
    test_circuit_breaker_flaky_redis: CircuitBreakerRedis,
    test_flaky_redis_connection: FlakyRedisConnection,
    test_short_redis_retry_wait: None,  # noqa: ARG001
) -> None:
    async def concurrent_coroutine() -> None:
        test_flaky_redis_connection.events.append("concurrent")

    await asyncio.gather(
        test_circuit_breaker_flaky_redis.is_host_available(host=SOME_HOST),
        concurrent_coroutine(),
    )

    assert test_flaky_redis_connection.events == ["attempt", "concurrent", "attempt"]


async def test_redis_circuit_breaker_preserves_attempt_count_and_reraise(
    test_circuit_breaker_flaky_redis: CircuitBreakerRedis,
    test_flaky_redis_connection: FlakyRedisConnection,
    test_short_redis_retry_wait: None,  # noqa: ARG001
) -> None:
    test_flaky_redis_connection.failing_attempts = REDIS_MAX_RETRIES

    with pytest.raises(RedisConnectionError):
        await test_circuit_breaker_flaky_redis.increment_failures_count(host=SOME_HOST)

    assert test_flaky_redis_connection.attempts == REDIS_MAX_RETRIES
