import abc
import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import ResponseType


logger = logging.getLogger(__name__)

P = typing.ParamSpec("P")


@dataclasses.dataclass(kw_only=True)
class BaseRetryer(abc.ABC, typing.Generic[ResponseType]):
    exceptions_to_retry: tuple[type[Exception]]
    max_retries: int

    @abc.abstractmethod
    async def retry(
        self,
        coroutine: typing.Callable[P, typing.Awaitable[ResponseType]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> ResponseType: ...

    @staticmethod
    def _log_attempts(retry_state: tenacity.RetryCallState) -> None:
        logger.info(
            "Attempt: attempt_number: %s, outcome_timestamp: %s",
            retry_state.attempt_number,
            retry_state.outcome_timestamp,
        )
