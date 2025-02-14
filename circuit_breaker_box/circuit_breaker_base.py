import abc
import dataclasses
import logging
import typing

import httpx
import tenacity

from circuit_breaker_box import errors


logger = logging.getLogger(__name__)


class UrlProtocol(typing.Protocol):
    host: str


class RequestProtocol(typing.Protocol):
    method: str
    url: httpx.URL


RequestType = typing.TypeVar("RequestType", bound=RequestProtocol)
ResponseType = typing.TypeVar("ResponseType")


@dataclasses.dataclass(kw_only=True, slots=True)
class BaseCircuitBreaker(typing.Generic[RequestType, ResponseType]):
    reset_timeout_in_seconds: int
    max_failure_count: int
    max_retries: int = 3
    exceptions_to_retry: typing.Sequence[type[Exception]]

    @abc.abstractmethod
    async def increment_failures_count(self, host: str) -> None: ...

    @abc.abstractmethod
    async def is_host_available(self, host: str) -> bool: ...

    @abc.abstractmethod
    async def raise_host_unavailable_error(self, host: str) -> typing.NoReturn: ...

    async def retry(
        self,
        awaitable: typing.Callable[[RequestType], typing.Awaitable[ResponseType]],
        request: RequestType,
        max_retries: int | None = None,
    ) -> ResponseType:
        async for attempt in tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(max_retries if max_retries else self.max_retries),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_exception_type(tuple(self.exceptions_to_retry)),
            reraise=True,
            before=self._log_attempts,
        ):
            with attempt:
                if not await self.is_host_available(request.url.host):
                    await self.raise_host_unavailable_error(request.url.host)

                if attempt.retry_state.attempt_number > 1:
                    await self.increment_failures_count(request.url.host)

                return await awaitable(request)

        raise errors.RetryFlowError

    @staticmethod
    def _log_attempts(retry_state: tenacity.RetryCallState) -> None:
        logger.info(
            "Attempt: attempt_number: %s, outcome_timestamp: %s",
            retry_state.attempt_number,
            retry_state.outcome_timestamp,
        )
