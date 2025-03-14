import asyncio
import logging
import typing

import fastapi
import httpx
import tenacity

from circuit_breaker_box import CircuitBreakerInMemory, Retrier


MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


class CustomCircuitBreakerInMemory(CircuitBreakerInMemory):
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        raise fastapi.HTTPException(status_code=500, detail=f"Host: {host} is unavailable")


async def main() -> None:
    """Use Retrier with CustomCircuitBreakerInMemory or CircuitBreakerRedis.

    coordinated retry/circuit breaking logic,
    also you can redefine raise_host_unavailable_error to raise some custom error in your application.
    """
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = CustomCircuitBreakerInMemory(
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
    )
    retryer = Retrier[httpx.Response](
        circuit_breaker=circuit_breaker,
        wait_strategy=tenacity.wait_exponential_jitter(),
        retry_cause=tenacity.retry_if_exception_type((ZeroDivisionError, httpx.RequestError)),
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
    )
    example_request = httpx.Request("GET", httpx.URL("http://example.com"))

    async def foo(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        raise ZeroDivisionError

    # will raise exception from circuit_breaker.raise_host_unavailable_error
    await retryer.retry(foo, example_request.url.host, example_request)


if __name__ == "__main__":
    asyncio.run(main())
