import typing

import fastapi
import httpx
import pytest

from circuit_breaker_box import CircuitBreakerInMemory, CircuitBreakerRedis, errors
from examples.example_circuit_breaker import CustomCircuitBreakerInMemory
from tests.conftest import SOME_HOST


async def test_circuit_breaker_in_memory(
    test_circuit_breaker_in_memory: CircuitBreakerInMemory[httpx.Request, httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_circuit_breaker_in_memory.retry(
        awaitable=bar, request=test_request, host=test_request.url.host
    )
    assert response.status_code == httpx.codes.OK

    async def foo(_: httpx.Request) -> typing.NoReturn:
        raise ZeroDivisionError

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_in_memory.retry(awaitable=foo, request=test_request, host=test_request.url.host)


async def test_circuit_breaker_redis(
    test_circuit_breaker_redis: CircuitBreakerRedis[httpx.Request, httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_circuit_breaker_redis.retry(awaitable=bar, request=test_request, host=test_request.url.host)
    assert response.status_code == httpx.codes.OK

    async def foo(_: httpx.Request) -> typing.NoReturn:
        raise ZeroDivisionError

    with pytest.raises(errors.HostUnavailableError):
        await test_circuit_breaker_redis.retry(awaitable=foo, request=test_request, host=test_request.url.host)


async def test_custom_circuit_breaker_in_memory(
    test_custom_circuit_breaker_in_memory: CustomCircuitBreakerInMemory[httpx.Request, httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_custom_circuit_breaker_in_memory.retry(
        awaitable=bar, request=test_request, host=test_request.url.host
    )
    assert response.status_code == httpx.codes.OK

    async def foo(_: httpx.Request) -> typing.NoReturn:
        raise ZeroDivisionError

    with pytest.raises(fastapi.exceptions.HTTPException):
        await test_custom_circuit_breaker_in_memory.retry(
            awaitable=foo, request=test_request, host=test_request.url.host
        )
