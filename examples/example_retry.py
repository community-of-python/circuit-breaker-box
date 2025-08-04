import asyncio
import logging

import httpx
import tenacity

from circuit_breaker_box.retrier import Retrier


MAX_RETRIES = 4
SOME_HOST = "http://example.com/"


async def main() -> None:
    """Use Retrier with tenacity adjustments.

     it automatically retry failed operations raising specific exceptions like:
         stop_rule
         retry_cause
         wait_strategy.

    `foo` as example function will be retried immediately (no wait) when it raises ZeroDivisionError up to MAX_RETRIES
        After exceeding MAX_RETRIES attempts, the exception will propagate.
    """
    logging.basicConfig(level=logging.DEBUG)
    retryer = Retrier[httpx.Response](
        stop_rule=tenacity.stop.stop_after_attempt(MAX_RETRIES),
        retry_cause=tenacity.retry_if_exception_type(ZeroDivisionError),
        wait_strategy=tenacity.wait_none(),
    )
    example_request = httpx.Request("GET", httpx.URL(SOME_HOST))

    async def foo(request: httpx.Request) -> httpx.Response:
        raise ZeroDivisionError(request)

    await retryer.retry(foo, request=example_request)


if __name__ == "__main__":
    asyncio.run(main())
