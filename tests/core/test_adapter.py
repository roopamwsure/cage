import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource


def _make_execution_attempt() -> ExecutionAttempt:
    action = Action(
        action_id="action-001",
        action_type="database.delete",
        principal=Principal(
            principal_id="principal-123",
        ),
        agent=Agent(
            agent_id="agent-456",
        ),
        resource=Resource(
            resource_id="database-789",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "database": "customers",
                "environment": "production",
            }
        ),
    )

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="delete-customers-production",
        action=action,
    )

    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    return ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )


def test_adapter_execution_result_records_state() -> None:
    execution_attempt = _make_execution_attempt()

    result = AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
    )

    assert result.result_id == "adapter-result-001"
    assert result.execution_attempt is execution_attempt
    assert result.state is AdapterExecutionState.ACKNOWLEDGED
    assert result.references == ()


def test_adapter_execution_result_preserves_references() -> None:
    result = AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=_make_execution_attempt(),
        state=AdapterExecutionState.ACKNOWLEDGED,
        references=[
            "request-id:123",
            "operation-id:456",
        ],
    )

    assert result.references == (
        "request-id:123",
        "operation-id:456",
    )


def test_adapter_execution_result_references_are_immutable() -> None:
    references = [
        "request-id:123",
    ]

    result = AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=_make_execution_attempt(),
        state=AdapterExecutionState.ACKNOWLEDGED,
        references=references,
    )

    references.append(
        "request-id:999",
    )

    assert result.references == (
        "request-id:123",
    )


def test_adapter_execution_result_requires_non_empty_identity() -> None:
    with pytest.raises(
        ValueError,
        match="result_id must not be empty",
    ):
        AdapterExecutionResult(
            result_id="   ",
            execution_attempt=_make_execution_attempt(),
            state=AdapterExecutionState.ACKNOWLEDGED,
        )


def test_adapter_execution_result_requires_execution_attempt() -> None:
    with pytest.raises(
        TypeError,
        match="execution_attempt must be an ExecutionAttempt",
    ):
        AdapterExecutionResult(
            result_id="adapter-result-001",
            execution_attempt="execution-attempt-001",  # type: ignore[arg-type]
            state=AdapterExecutionState.ACKNOWLEDGED,
        )


def test_adapter_execution_result_requires_adapter_state() -> None:
    with pytest.raises(
        TypeError,
        match="state must be an AdapterExecutionState",
    ):
        AdapterExecutionResult(
            result_id="adapter-result-001",
            execution_attempt=_make_execution_attempt(),
            state="acknowledged",  # type: ignore[arg-type]
        )


def test_adapter_execution_result_rejects_blank_reference() -> None:
    with pytest.raises(ValueError):
        AdapterExecutionResult(
            result_id="adapter-result-001",
            execution_attempt=_make_execution_attempt(),
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=[
                "   ",
            ],
        )


@pytest.mark.parametrize(
    "state",
    [
        AdapterExecutionState.ACKNOWLEDGED,
        AdapterExecutionState.REJECTED,
        AdapterExecutionState.ERROR,
        AdapterExecutionState.UNKNOWN,
    ],
)
def test_adapter_execution_states_are_request_level_only(
    state: AdapterExecutionState,
) -> None:
    result = AdapterExecutionResult(
        result_id=f"adapter-result-{state.value}",
        execution_attempt=_make_execution_attempt(),
        state=state,
    )

    assert result.state is state
    assert not hasattr(result, "effect")
    assert not hasattr(result, "effect_state")