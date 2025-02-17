import asyncio
import logging
import typing

import fastapi
import httpx

from circuit_breaker_box import CircuitBreakerInMemory
from circuit_breaker_box.circuit_breaker_base import RequestType, ResponseType


HTTP_MAX_TRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 3
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


class CustomCircuitBreakerInMemory(CircuitBreakerInMemory[RequestType, ResponseType]):
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn:
        raise fastapi.HTTPException(status_code=500, detail=f"Host: {host} is unavailable")


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    circuit_breaker = CustomCircuitBreakerInMemory[httpx.Request, httpx.Response](
        reset_timeout_in_seconds=RESET_TIMEOUT_IN_SECONDS,
        max_failure_count=CIRCUIT_BREAKER_MAX_FAILURE_COUNT,
        max_cache_size=MAX_CACHE_SIZE,
        exceptions_to_retry=(ZeroDivisionError,),
    )

    example_request = httpx.Request("GET", httpx.URL("http://example.com"))

    async def foo(_: httpx.Request) -> httpx.Response:
        raise ZeroDivisionError

    await circuit_breaker.retry(awaitable=foo, request=example_request, host=example_request.url.host)


if __name__ == "__main__":
    asyncio.run(main())
