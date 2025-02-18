import asyncio
import logging

import httpx

from circuit_breaker_box.retryers import Retrier


MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 3
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


async def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    retryer = Retrier[httpx.Response](
        max_retries=MAX_RETRIES,
        exceptions_to_retry=(ZeroDivisionError,),
    )
    example_request = httpx.Request("GET", httpx.URL("http://example.com"))

    async def foo(request: httpx.Request, host: str) -> httpx.Response:  # noqa: ARG001
        raise ZeroDivisionError

    await retryer.retry(coroutine=foo, request=example_request, host=example_request.url.host)


if __name__ == "__main__":
    asyncio.run(main())
