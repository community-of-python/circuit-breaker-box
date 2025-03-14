import asyncio
import logging

from circuit_breaker_box import CircuitBreakerInMemory


MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = CircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )
    # circuit_breaker is open state for SOME_HOST
    assert await circuit_breaker.is_host_available(host=SOME_HOST)

    for _ in range(MAX_RETRIES):
        # circuit_breaker is half-open for SOME_HOST
        await circuit_breaker.increment_failures_count(host=SOME_HOST)

    # after failure count more then CIRCUIT_BREAKER_MAX_FAILURE_COUNT value circuit_breaker is closed
    assert await circuit_breaker.is_host_available(host=SOME_HOST) is False

    # close state reset to open state after RESET_TIMEOUT_IN_SECONDS delay
    await asyncio.sleep(RESET_TIMEOUT_IN_SECONDS)
    assert await circuit_breaker.is_host_available(host=SOME_HOST) is True


if __name__ == "__main__":
    asyncio.run(main())
