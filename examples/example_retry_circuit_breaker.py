import asyncio
import logging
import typing

import fastapi
import httpx

from circuit_breaker_box import CircuitBreakerInMemory, RetrierCircuitBreaker


MAX_RETRIES = 4
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
    retryer = RetrierCircuitBreaker[httpx.Response](
        circuit_breaker=circuit_breaker,
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(ZeroDivisionError, httpx.RequestError),
    )
    example_request = httpx.Request("GET", httpx.URL("http://example.com"))

    async def foo(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        raise ZeroDivisionError

    # will raise exception from circuit_breaker.raise_host_unavailable_error
    await retryer.retry(foo, example_request.url.host, example_request)


if __name__ == "__main__":
    asyncio.run(main())
