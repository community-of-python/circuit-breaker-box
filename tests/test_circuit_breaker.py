import fastapi
import pytest

from circuit_breaker import errors
from circuit_breaker.circuit_breaker import CircuitBreakerInMemory, CircuitBreakerRedis
from examples.example_circuit_breaker import CustomCircuitBreakerInMemory
from tests.conftest import HTTP_MAX_TRIES, SOME_HOST


async def test_circuit_breaker_in_memory(test_circuit_breaker_in_memory: CircuitBreakerInMemory) -> None:
    assert await test_circuit_breaker_in_memory.is_host_available(host=SOME_HOST)

    for _ in range(HTTP_MAX_TRIES):
        await test_circuit_breaker_in_memory.increment_failures_count(host=SOME_HOST)

    assert await test_circuit_breaker_in_memory.is_host_available(host=SOME_HOST) is False

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_in_memory.raise_host_unavailable_error(host=SOME_HOST)


async def test_circuit_breaker_redis(test_circuit_breaker_redis: CircuitBreakerRedis) -> None:
    assert await test_circuit_breaker_redis.is_host_available(host=SOME_HOST)

    for _ in range(HTTP_MAX_TRIES):
        await test_circuit_breaker_redis.increment_failures_count(host=SOME_HOST)

    assert await test_circuit_breaker_redis.is_host_available(host=SOME_HOST) is False

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_redis.raise_host_unavailable_error(host=SOME_HOST)


async def test_custom_circuit_breaker_in_memory(
    test_custom_circuit_breaker_in_memory: CustomCircuitBreakerInMemory,
) -> None:
    assert await test_custom_circuit_breaker_in_memory.is_host_available(host=SOME_HOST)

    for _i in range(HTTP_MAX_TRIES):
        await test_custom_circuit_breaker_in_memory.increment_failures_count(host=SOME_HOST)

    assert await test_custom_circuit_breaker_in_memory.is_host_available(host=SOME_HOST) is False

    with pytest.raises(fastapi.HTTPException, match=f"Host: {SOME_HOST} is unavailable"):
        await test_custom_circuit_breaker_in_memory.raise_host_unavailable_error(host=SOME_HOST)
