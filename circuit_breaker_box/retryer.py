import abc
import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import BaseCircuitBreaker, ResponseType
from circuit_breaker_box.common_types import retry_clause_types, stop_types, wait_types


logger = logging.getLogger(__name__)

P = typing.ParamSpec("P")


@dataclasses.dataclass(kw_only=True)
class Retrier(abc.ABC, typing.Generic[ResponseType]):
    reraise: bool = True
    wait_strategy: wait_types
    stop_rule: stop_types
    retry_cause: retry_clause_types
    circuit_breaker: BaseCircuitBreaker | None = None

    async def retry(  # type: ignore[return]
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        /,
        host: str | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType:
        if not host and self.circuit_breaker:
            msg = "'host' argument should be defined"
            raise ValueError(msg)

        for attempt in tenacity.Retrying(  # noqa: RET503
            stop=self.stop_rule,
            wait=self.wait_strategy,
            retry=self.retry_cause,
            reraise=self.reraise,
            before=self.do_before_attempts,
            after=self.do_after_attempts,
        ):
            with attempt:
                if self.circuit_breaker and host:
                    if not await self.circuit_breaker.is_host_available(host):
                        await self.circuit_breaker.raise_host_unavailable_error(host)

                    if attempt.retry_state.attempt_number > 1:
                        await self.circuit_breaker.increment_failures_count(host)

                return await coroutine(*args, **kwargs)

    @staticmethod
    def do_before_attempts(retry_state: tenacity.RetryCallState) -> None:
        pass

    @staticmethod
    def do_after_attempts(retry_state: tenacity.RetryCallState) -> None:
        logger.warning(
            "Attempt: attempt_number: %s, result: %s",
            retry_state.attempt_number,
            str(retry_state.outcome).split("state=")[-1],
        )
