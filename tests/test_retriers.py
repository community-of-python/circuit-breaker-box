import typing

import fastapi.exceptions
import httpx
import pytest

from circuit_breaker_box import Retryer, RetryerCircuitBreaker
from tests.conftest import SOME_HOST


async def test_retry(
    test_retry_without_circuit_breaker: Retryer[httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_retry_without_circuit_breaker.retry(coroutine=bar, request=test_request)
    assert response.status_code == httpx.codes.OK

    async def foo(request: httpx.Request) -> typing.NoReturn:  # noqa: ARG001
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await test_retry_without_circuit_breaker.retry(coroutine=foo, request=test_request)


async def test_retry_custom_circuit_breaker(
    test_retry_custom_circuit_breaker_in_memory: RetryerCircuitBreaker[httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(request: httpx.Request, host: str) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_retry_custom_circuit_breaker_in_memory.retry(
        coroutine=bar, request=test_request, host=test_request.url.host
    )
    assert response.status_code == httpx.codes.OK

    async def foo(request: httpx.Request, host: str) -> typing.NoReturn:  # noqa: ARG001
        raise ZeroDivisionError

    with pytest.raises(fastapi.exceptions.HTTPException, match=f"500: Host: {test_request.url.host} is unavailable"):
        await test_retry_custom_circuit_breaker_in_memory.retry(
            coroutine=foo, request=test_request, host=test_request.url.host
        )

    with pytest.raises(ValueError, match="'host' argument should be defined"):
        await test_retry_custom_circuit_breaker_in_memory.retry(  # type: ignore[call-arg]
            coroutine=foo,
            request=test_request,
        )
