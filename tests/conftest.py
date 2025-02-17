import logging

import httpx
import pytest

from circuit_breaker_box import CircuitBreakerInMemory, Retryer, RetryerCircuitBreaker
from examples.example_retry_circuit_breaker import CustomCircuitBreakerInMemory


logger = logging.getLogger(__name__)

MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


@pytest.fixture(name="test_circuit_breaker_in_memory")
def fixture_circuit_breaker_in_memory() -> CircuitBreakerInMemory:
    return CircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )


@pytest.fixture(name="test_custom_circuit_breaker_in_memory")
def fixture_custom_circuit_breaker_in_memory() -> CustomCircuitBreakerInMemory:
    return CustomCircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )


@pytest.fixture(name="test_retry_without_circuit_breaker")
def fixture_retry_without_circuit_breaker() -> Retryer[httpx.Response]:
    return Retryer[httpx.Response](
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(ZeroDivisionError,),
    )


@pytest.fixture(name="test_retry_custom_circuit_breaker_in_memory")
def fixture_retry_custom_circuit_breaker_in_memory(
    test_custom_circuit_breaker_in_memory: CustomCircuitBreakerInMemory,
) -> RetryerCircuitBreaker[httpx.Response]:
    return RetryerCircuitBreaker[httpx.Response](
        circuit_breaker=test_custom_circuit_breaker_in_memory,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(ZeroDivisionError,),
    )
