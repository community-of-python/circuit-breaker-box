import abc
import dataclasses
import logging
import typing

import tenacity

from circuit_breaker_box import ResponseType


logger = logging.getLogger(__name__)

P = typing.ParamSpec("P")


@dataclasses.dataclass(kw_only=True)
class BaseRetrier(abc.ABC, typing.Generic[ResponseType]):
    max_retries: int
    reraise: bool = True
    exceptions_to_retry: tuple[type[Exception]]
    stop: tenacity.stop.stop_after_attempt = dataclasses.field(init=False)
    wait_strategy: tenacity.wait.wait_exponential_jitter = dataclasses.field(init=False)
    retry_cause: tenacity.retry_if_exception_type = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.stop = tenacity.stop_after_attempt(self.max_retries)
        self.wait_strategy = tenacity.wait_exponential_jitter()
        self.retry_cause = tenacity.retry_if_exception_type(self.exceptions_to_retry)

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
