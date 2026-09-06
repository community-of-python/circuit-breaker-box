import dataclasses
import logging
import typing

import httpx
import pytest
import tenacity
from redis import asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from circuit_breaker_box import BaseCircuitBreaker, CircuitBreakerInMemory, Retrier, errors
from circuit_breaker_box.circuit_breaker_redis import CircuitBreakerRedis
from examples.example_retry_circuit_breaker import CustomCircuitBreakerInMemory


logger = logging.getLogger(__name__)

MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"
RETRY_WAIT_IN_SECONDS = 0.05
REDIS_MAX_RETRIES = 3


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


@pytest.fixture(name="test_retry_without_circuit_breaker")
def fixture_retry_without_circuit_breaker() -> Retrier[httpx.Response]:
    return Retrier[httpx.Response](
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_none(),
    )


@pytest.fixture(name="test_retry_custom_circuit_breaker_in_memory")
def fixture_retry_custom_circuit_breaker_in_memory(
    test_custom_circuit_breaker_in_memory: CustomCircuitBreakerInMemory,
) -> Retrier[httpx.Response]:
    return Retrier[httpx.Response](
        circuit_breaker=test_custom_circuit_breaker_in_memory,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_none(),
    )


@pytest.fixture(name="test_retry_with_wait_without_circuit_breaker")
def fixture_retry_with_wait_without_circuit_breaker() -> Retrier[None]:
    return Retrier[None](
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_fixed(RETRY_WAIT_IN_SECONDS),
    )


@pytest.fixture(name="test_retry_without_reraise")
def fixture_retry_without_reraise() -> Retrier[None]:
    return Retrier[None](
        reraise=False,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_none(),
    )


@dataclasses.dataclass(kw_only=True, slots=True)
class RecordingCircuitBreaker(BaseCircuitBreaker):
    calls: list[str] = dataclasses.field(default_factory=list)
    available_for_first_checks: int = MAX_RETRIES
    availability_checks: int = 0

    async def increment_failures_count(self, host: str) -> None:
        self.calls.append(f"increment_failures_count:{host}")

    async def is_host_available(self, host: str) -> bool:
        self.calls.append(f"is_host_available:{host}")
        self.availability_checks += 1
        return self.availability_checks <= self.available_for_first_checks

    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        self.calls.append(f"raise_host_unavailable_error:{host}")
        raise errors.HostUnavailableError(host)


@pytest.fixture(name="test_recording_circuit_breaker")
def fixture_recording_circuit_breaker() -> RecordingCircuitBreaker:
    return RecordingCircuitBreaker(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
    )


@pytest.fixture(name="test_retry_recording_circuit_breaker")
def fixture_retry_recording_circuit_breaker(
    test_recording_circuit_breaker: RecordingCircuitBreaker,
) -> Retrier[None]:
    return Retrier[None](
        circuit_breaker=test_recording_circuit_breaker,
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_none(),
    )


@dataclasses.dataclass
class FlakyRedisConnection(aioredis.Redis):  # type: ignore[type-arg]
    events: list[str] = dataclasses.field(default_factory=list)
    failing_attempts: int = 1
    attempts: int = 0

    def _record_attempt(self, host: str | bytes) -> None:
        logger.debug("host: %s, attempts: %d", host, self.attempts)
        self.events.append("attempt")
        self.attempts += 1
        if self.attempts <= self.failing_attempts:
            raise RedisConnectionError

    async def incr(self, host: str | bytes, amount: int = 1) -> int:
        self._record_attempt(host)
        return amount

    async def expire(self, *args: typing.Any, **kwargs: typing.Any) -> bool:  # noqa: ANN401
        logger.debug(args, kwargs)
        return True

    async def get(self, host: str | bytes) -> int:
        self._record_attempt(host)
        return 0


@pytest.fixture(name="test_flaky_redis_connection")
def fixture_flaky_redis_connection() -> FlakyRedisConnection:
    return FlakyRedisConnection()


@pytest.fixture(name="test_circuit_breaker_flaky_redis")
def fixture_circuit_breaker_flaky_redis(test_flaky_redis_connection: FlakyRedisConnection) -> CircuitBreakerRedis:
    return CircuitBreakerRedis(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        redis_connection=test_flaky_redis_connection,
    )


@pytest.fixture(name="test_short_redis_retry_wait")
def fixture_short_redis_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shorten the redis backoff so the tests do not spend seconds asleep.

    CircuitBreakerRedis builds its wait strategy per call, so replacing the constructor is enough.
    Only the delay changes: the stop rule, retry causes, reraise and before callback stay as they are.
    """

    def build_short_wait(*args: typing.Any, **kwargs: typing.Any) -> tenacity.wait_fixed:  # noqa: ANN401, ARG001
        return tenacity.wait_fixed(RETRY_WAIT_IN_SECONDS)

    monkeypatch.setattr(tenacity, "wait_exponential_jitter", build_short_wait)
