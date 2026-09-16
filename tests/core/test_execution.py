import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource


def _make_decision() -> Decision:
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

    return Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )


def test_execution_attempt_records_identity_and_decision() -> None:
    decision = _make_decision()

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )

    assert (
        execution_attempt.execution_attempt_id
        == "execution-attempt-001"
    )
    assert execution_attempt.decision is decision
    assert execution_attempt.previous_execution_attempt_id is None


def test_execution_attempt_derives_consequence_from_decision() -> None:
    decision = _make_decision()

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )

    assert (
        execution_attempt.consequence
        is decision.attempt.consequence
    )
    assert (
        execution_attempt.consequence.consequence_id
        == "consequence-001"
    )


def test_execution_attempt_can_reference_previous_execution_attempt() -> None:
    decision = _make_decision()

    first = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )

    second = ExecutionAttempt(
        execution_attempt_id="execution-attempt-002",
        decision=decision,
        previous_execution_attempt_id=(
            first.execution_attempt_id
        ),
    )

    assert (
        second.previous_execution_attempt_id
        == first.execution_attempt_id
    )

    assert second.execution_attempt_id != first.execution_attempt_id

    assert second.consequence is first.consequence


def test_execution_attempt_requires_non_empty_identity() -> None:
    decision = _make_decision()

    with pytest.raises(
        ValueError,
        match="execution_attempt_id must not be empty",
    ):
        ExecutionAttempt(
            execution_attempt_id="   ",
            decision=decision,
        )


def test_execution_attempt_requires_decision() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a Decision",
    ):
        ExecutionAttempt(
            execution_attempt_id="execution-attempt-001",
            decision="decision-001",  # type: ignore[arg-type]
        )


def test_execution_attempt_rejects_blank_previous_identity() -> None:
    decision = _make_decision()

    with pytest.raises(
        ValueError,
        match="previous_execution_attempt_id must not be empty",
    ):
        ExecutionAttempt(
            execution_attempt_id="execution-attempt-002",
            decision=decision,
            previous_execution_attempt_id="   ",
        )


def test_execution_attempt_cannot_reference_itself_as_previous() -> None:
    decision = _make_decision()

    with pytest.raises(
        ValueError,
        match=(
            "previous_execution_attempt_id must differ "
            "from execution_attempt_id"
        ),
    ):
        ExecutionAttempt(
            execution_attempt_id="execution-attempt-001",
            decision=decision,
            previous_execution_attempt_id=(
                "execution-attempt-001"
            ),
        )


def test_execution_attempt_is_immutable() -> None:
    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=_make_decision(),
    )

    with pytest.raises(AttributeError):
        execution_attempt.execution_attempt_id = (
            "execution-attempt-002"
        )