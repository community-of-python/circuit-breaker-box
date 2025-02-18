import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import BaseCircuitBreaker, BaseRetrier, ResponseType


logger = logging.getLogger(__name__)

P = typing.ParamSpec("P")


@dataclasses.dataclass(kw_only=True)
class Retrier(BaseRetrier[ResponseType]):
    async def retry(  # type: ignore[return]
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType:
        for attempt in tenacity.Retrying(  # noqa: RET503
            stop=self.stop,
            wait=self.wait_strategy,
            retry=self.retry_cause,
            reraise=self.reraise,
            before=self._log_attempts,
        ):
            with attempt:
                return await coroutine(*args, **kwargs)


@dataclasses.dataclass(kw_only=True)
class RetrierCircuitBreaker(BaseRetrier[ResponseType]):
    circuit_breaker: BaseCircuitBreaker

    async def retry(  # type: ignore[return]
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        /,
        host: str,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType:
        if not host:
            msg = "'host' argument should be defined"
            raise ValueError(msg)

        for attempt in tenacity.Retrying(  # noqa: RET503
            stop=self.stop,
            wait=self.wait_strategy,
            retry=self.retry_cause,
            reraise=self.reraise,
            before=self._log_attempts,
        ):
            with attempt:
                if not await self.circuit_breaker.is_host_available(host):
                    await self.circuit_breaker.raise_host_unavailable_error(host)

                if attempt.retry_state.attempt_number > 1:
                    await self.circuit_breaker.increment_failures_count(host)

                return await coroutine(*args, **kwargs)
