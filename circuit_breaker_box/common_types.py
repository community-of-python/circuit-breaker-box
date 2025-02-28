import typing

import tenacity


ResponseType = typing.TypeVar("ResponseType")

stop_types = (
    tenacity.stop.stop_after_attempt
    | tenacity.stop.stop_all
    | tenacity.stop.stop_any
    | tenacity.stop.stop_when_event_set
    | tenacity.stop.stop_after_delay
    | tenacity.stop.stop_before_delay
)
wait_types = (
    tenacity.wait.wait_fixed
    | tenacity.wait.wait_none
    | tenacity.wait.wait_random
    | tenacity.wait.wait_combine
    | tenacity.wait.wait_chain
    | tenacity.wait.wait_incrementing
    | tenacity.wait.wait_exponential
    | tenacity.wait.wait_random_exponential
    | tenacity.wait.wait_exponential_jitter
)
retry_clause_types = (
    tenacity.retry_if_exception
    | tenacity.retry_if_exception_type
    | tenacity.retry_if_not_exception_type
    | tenacity.retry_unless_exception_type
    | tenacity.retry_if_exception_cause_type
    | tenacity.retry_if_result
    | tenacity.retry_if_not_result
    | tenacity.retry_if_exception_message
    | tenacity.retry_if_not_exception_message
    | tenacity.retry_any
    | tenacity.retry_all
)
