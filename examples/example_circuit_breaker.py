import asyncio
import logging
import typing

import fastapi

from circuit_breaker_box import CircuitBreakerInMemory


HTTP_MAX_TRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


class CustomCircuitBreakerInMemory(CircuitBreakerInMemory):
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        raise fastapi.HTTPException(status_code=500, detail=f"Host: {host} is unavailable")


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = CustomCircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )

    assert await circuit_breaker.is_host_available(host=SOME_HOST)

    for _ in range(HTTP_MAX_TRIES):
        await circuit_breaker.increment_failures_count(host=SOME_HOST)

    assert await circuit_breaker.is_host_available(host=SOME_HOST) is False


if __name__ == "__main__":
    asyncio.run(main())
