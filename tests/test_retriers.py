import asyncio
import typing

import fastapi.exceptions
import httpx
import pytest
import tenacity

from circuit_breaker_box import Retrier, errors
from tests.conftest import MAX_RETRIES, SOME_HOST, RecordingCircuitBreaker


async def test_retry(
    test_retry_without_circuit_breaker: Retrier[httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_retry_without_circuit_breaker.retry(bar, request=test_request)
    assert response.status_code == httpx.codes.OK

    async def foo(request: httpx.Request) -> typing.NoReturn:  # noqa: ARG001
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await test_retry_without_circuit_breaker.retry(foo, request=test_request)


async def test_retry_custom_circuit_breaker(
    test_retry_custom_circuit_breaker_in_memory: Retrier[httpx.Response],
) -> None:
    test_request = httpx.AsyncClient().build_request(method="GET", url=SOME_HOST)

    async def bar(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(status_code=httpx.codes.OK)

    response = await test_retry_custom_circuit_breaker_in_memory.retry(bar, test_request.url.host, request=test_request)
    assert response.status_code == httpx.codes.OK

    async def foo(request: httpx.Request) -> typing.NoReturn:  # noqa: ARG001
        raise ZeroDivisionError

    with pytest.raises(fastapi.exceptions.HTTPException, match=f"500: Host: {test_request.url.host} is unavailable"):
        await test_retry_custom_circuit_breaker_in_memory.retry(foo, host=test_request.url.host, request=test_request)

    with pytest.raises(ValueError, match="'host' argument should be defined"):
        await test_retry_custom_circuit_breaker_in_memory.retry(
            foo,
            request=test_request,
            host="",
        )


async def test_retry_does_not_block_event_loop_while_waiting(
    test_retry_with_wait_without_circuit_breaker: Retrier[None],
) -> None:
    events: list[str] = []

    async def fail_once() -> None:
        events.append("attempt")
        if events.count("attempt") == 1:
            raise ZeroDivisionError

    async def concurrent_coroutine() -> None:
        events.append("concurrent")

    await asyncio.gather(test_retry_with_wait_without_circuit_breaker.retry(fail_once), concurrent_coroutine())

    assert events == ["attempt", "concurrent", "attempt"]


async def test_retry_preserves_attempt_count_and_callbacks(
    test_retry_without_circuit_breaker: Retrier[httpx.Response],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    callbacks: list[str] = []

    def record_before(retry_state: tenacity.RetryCallState) -> None:
        callbacks.append(f"before:{retry_state.attempt_number}")

    def record_after(retry_state: tenacity.RetryCallState) -> None:
        callbacks.append(f"after:{retry_state.attempt_number}")

    monkeypatch.setattr(test_retry_without_circuit_breaker, "do_before_attempts", record_before)
    monkeypatch.setattr(test_retry_without_circuit_breaker, "do_after_attempts", record_after)

    async def always_fails() -> typing.NoReturn:
        nonlocal attempts
        attempts += 1
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await test_retry_without_circuit_breaker.retry(always_fails)

    assert attempts == MAX_RETRIES
    assert callbacks == [
        call
        for attempt_number in range(1, MAX_RETRIES + 1)
        for call in (f"before:{attempt_number}", f"after:{attempt_number}")
    ]


async def test_retry_preserves_reraise_disabled(
    test_retry_without_reraise: Retrier[None],
) -> None:
    attempts = 0

    async def always_fails() -> typing.NoReturn:
        nonlocal attempts
        attempts += 1
        raise ZeroDivisionError

    with pytest.raises(tenacity.RetryError):
        await test_retry_without_reraise.retry(always_fails)

    assert attempts == MAX_RETRIES


async def test_retry_preserves_retry_predicate(
    test_retry_without_circuit_breaker: Retrier[httpx.Response],
) -> None:
    attempts = 0

    async def raises_unretried_error() -> typing.NoReturn:
        nonlocal attempts
        attempts += 1
        raise RuntimeError

    with pytest.raises(RuntimeError):
        await test_retry_without_circuit_breaker.retry(raises_unretried_error)

    assert attempts == 1


async def test_retry_preserves_circuit_breaker_interaction_order(
    test_retry_recording_circuit_breaker: Retrier[None],
    test_recording_circuit_breaker: RecordingCircuitBreaker,
) -> None:
    async def always_fails() -> typing.NoReturn:
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await test_retry_recording_circuit_breaker.retry(always_fails, SOME_HOST)

    assert test_recording_circuit_breaker.calls == [
        f"is_host_available:{SOME_HOST}",
        *[
            call
            for _ in range(MAX_RETRIES - 1)
            for call in (f"is_host_available:{SOME_HOST}", f"increment_failures_count:{SOME_HOST}")
        ],
    ]


async def test_retry_stops_on_unavailable_host_reported_by_circuit_breaker(
    test_retry_recording_circuit_breaker: Retrier[None],
    test_recording_circuit_breaker: RecordingCircuitBreaker,
) -> None:
    test_recording_circuit_breaker.available_for_first_checks = 2

    async def always_fails() -> typing.NoReturn:
        raise ZeroDivisionError

    with pytest.raises(errors.HostUnavailableError):
        await test_retry_recording_circuit_breaker.retry(always_fails, SOME_HOST)

    assert test_recording_circuit_breaker.calls == [
        f"is_host_available:{SOME_HOST}",
        f"is_host_available:{SOME_HOST}",
        f"increment_failures_count:{SOME_HOST}",
        f"is_host_available:{SOME_HOST}",
        f"raise_host_unavailable_error:{SOME_HOST}",
    ]
