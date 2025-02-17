import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import BaseCircuitBreaker, BaseRetryer, ResponseType, errors


logger = logging.getLogger(__name__)

P = typing.ParamSpec("P")


@dataclasses.dataclass(kw_only=True)
class Retryer(BaseRetryer[ResponseType]):
    async def retry(
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType:
        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_attempt(self.max_retries),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_exception_type(self.exceptions_to_retry),
            reraise=True,
            before=self._log_attempts,
        ):
            with attempt:
                return await coroutine(*args, **kwargs)

        raise errors.RetryFlowError


@dataclasses.dataclass(kw_only=True)
class RetryerCircuitBreaker(BaseRetryer[ResponseType]):
    circuit_breaker: BaseCircuitBreaker

    async def retry(
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType:
        if not (host := str(kwargs.get("host", ""))):
            msg = "'host' argument should be defined"
            raise ValueError(msg)

        for attempt in tenacity.Retrying(
            stop=tenacity.stop_after_attempt(self.max_retries),
            wait=tenacity.wait_exponential_jitter(),
            retry=tenacity.retry_if_exception_type(self.exceptions_to_retry),
            reraise=True,
            before=self._log_attempts,
        ):
            with attempt:
                if not await self.circuit_breaker.is_host_available(host):
                    await self.circuit_breaker.raise_host_unavailable_error(host)

                if attempt.retry_state.attempt_number > 1:
                    await self.circuit_breaker.increment_failures_count(host)

                return await coroutine(*args, **kwargs)

        raise errors.RetryFlowError
