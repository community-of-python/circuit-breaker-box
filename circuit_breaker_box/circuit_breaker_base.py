import abc
import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import errors


logger = logging.getLogger(__name__)


RequestType = typing.TypeVar("RequestType")
ResponseType = typing.TypeVar("ResponseType")


@dataclasses.dataclass(kw_only=True, slots=True)
class BaseCircuitBreaker(typing.Generic[RequestType, ResponseType]):
    reset_timeout_in_seconds: int
    max_failure_count: int
    exceptions_to_retry: tuple[type[Exception]]
    max_retries: int

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
        host: str,
        max_retries: int | None = None,
    ) -> ResponseType:
        async for attempt in tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(max_retries if max_retries else self.max_retries),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_exception_type(self.exceptions_to_retry),
            reraise=True,
            before=self._log_attempts,
        ):
            with attempt:
                if not await self.is_host_available(host):
                    await self.raise_host_unavailable_error(host)

                if attempt.retry_state.attempt_number > 1:
                    await self.increment_failures_count(host)

                return await awaitable(request)

        raise errors.RetryFlowError

    @staticmethod
    def _log_attempts(retry_state: tenacity.RetryCallState) -> None:
        logger.info(
            "Attempt: attempt_number: %s, outcome_timestamp: %s",
            retry_state.attempt_number,
            retry_state.outcome_timestamp,
        )
