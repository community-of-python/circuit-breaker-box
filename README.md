# Python Circuit Breaker Box

A Python implementation of the Circuit Breaker pattern.

## Features

- 🚀 Implementations:
  - **Redis-based**
  - **In-memory**
- [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=FFD43B)](https://python.org) 3.10-3.13 support.
- ⚡ Asynchronous API
- 🔧 Configurable parameters
- 🔄 Retries by [tenacity](https://tenacity.readthedocs.io/en/latest/)
- 🛠️ FastAPI integration through custom exceptions

## Installation
```bash
pip install circuit-breaker-box
```

## Usage
### Direct usage
```python
import asyncio
import logging

from circuit_breaker_box import CircuitBreakerInMemory


MAX_RETRIES = 4
MAX_CACHE_SIZE = 256
CIRCUIT_BREAKER_MAX_FAILURE_COUNT = 1
RESET_TIMEOUT_IN_SECONDS = 10
SOME_HOST = "http://example.com/"


async def main() -> None:
    """Define CircuitBreakerInMemory or CircuitBreakerRedis and use in your application directly"""
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


>>> circuit_breaker_box.circuit_breaker_in_memory:host: 'http://example.com/', failures_count: '0', self.max_failure_count: '1', is_available: 'True'
>>> circuit_breaker_box.circuit_breaker_in_memory:Added host: http://example.com/, errors: 1
>>> circuit_breaker_box.circuit_breaker_in_memory:Incremented error for host: 'http://example.com/', errors: 2
>>> circuit_breaker_box.circuit_breaker_in_memory:Incremented error for host: 'http://example.com/', errors: 3
>>> circuit_breaker_box.circuit_breaker_in_memory:Incremented error for host: 'http://example.com/', errors: 4
>>> circuit_breaker_box.circuit_breaker_in_memory:host: 'http://example.com/', failures_count: '4', self.max_failure_count: '1', is_available: 'False'
>>> circuit_breaker_box.circuit_breaker_in_memory:host: 'http://example.com/', failures_count: '0', self.max_failure_count: '1', is_available: 'True'
```

### Retrier
```python
import asyncio
import logging

import httpx
import tenacity

from circuit_breaker_box.retryer import Retrier


MAX_RETRIES = 4
SOME_HOST = "http://example.com/"


async def main() -> None:
    """
    Use Retrier with tenacity adjustments to automatically retry failed operations raising specific exceptions like:
     stop_rule
     retry_cause
     wait_strategy

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


>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 1, outcome_timestamp: None
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 2, outcome_timestamp: None
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 3, outcome_timestamp: None
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 4, outcome_timestamp: None
>>> Traceback (most recent call last):
>>>     ...
>>> ZeroDivisionError: <Request('GET', 'http://example.com/')>
```

### Retrier with CircuitBreaker
```python
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

>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 1, outcome_timestamp: None
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:host: 'example.com', failures_count: '0', self.max_failure_count: '1', is_available: 'True'
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 2, outcome_timestamp: None
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:host: 'example.com', failures_count: '0', self.max_failure_count: '1', is_available: 'True'
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:Added host: example.com, errors: 1
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 3, outcome_timestamp: None
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:host: 'example.com', failures_count: '1', self.max_failure_count: '1', is_available: 'True'
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:Incremented error for host: 'example.com', errors: 2
>>> INFO:circuit_breaker_box.retryer:Attempt: attempt_number: 4, outcome_timestamp: None
>>> DEBUG:circuit_breaker_box.circuit_breaker_in_memory:host: 'example.com', failures_count: '2', self.max_failure_count: '1', is_available: 'False'
>>> Traceback (most recent call last):
>>>     ...
>>> fastapi.exceptions.HTTPException: 500: Host: example.com is unavailable
```

See -> [Examples](examples/)

## Development
### Commands
Use -> [Justfile](Justfile)
