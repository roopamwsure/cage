import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
    EffectAdapter,
)
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
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


def _make_capability(
    execution_attempt: ExecutionAttempt,
) -> ExecutionCapability:
    action = execution_attempt.consequence.action

    return ExecutionCapability(
        capability_id="capability-001",
        consequence_id=(
            execution_attempt.consequence.consequence_id
        ),
        action_type=action.action_type,
        resource_id=action.resource.resource_id,
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
            execution_attempt=(
                "execution-attempt-001"  # type: ignore[arg-type]
            ),
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


def test_effect_adapter_protocol_accepts_structural_implementation() -> None:
    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            return AdapterExecutionResult(
                result_id="adapter-result-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
            )

    adapter = TestAdapter()

    assert isinstance(adapter, EffectAdapter)


def test_effect_adapter_receives_exact_execution_inputs() -> None:
    received: dict[str, object] = {}

    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            received["execution_attempt"] = execution_attempt
            received["effect"] = effect
            received["capability"] = capability

            return AdapterExecutionResult(
                result_id="adapter-result-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
                references=[
                    "request-id:123",
                ],
            )

    execution_attempt = _make_execution_attempt()

    effect = (
        execution_attempt
        .consequence
        .action
        .requested_effect
    )

    capability = _make_capability(
        execution_attempt,
    )

    adapter = TestAdapter()

    result = adapter.execute(
        execution_attempt=execution_attempt,
        effect=effect,
        capability=capability,
    )

    assert received["execution_attempt"] is execution_attempt
    assert received["effect"] is effect
    assert received["capability"] is capability

    assert isinstance(
        result,
        AdapterExecutionResult,
    )

    assert result.execution_attempt is execution_attempt
    assert result.state is AdapterExecutionState.ACKNOWLEDGED

    assert result.references == (
        "request-id:123",
    )

    assert not hasattr(result, "effect")
    assert not hasattr(result, "effect_state")


def test_effect_adapter_can_receive_narrowed_effect_only() -> None:
    base_execution_attempt = _make_execution_attempt()

    permitted_effect = RequestedEffect(
        parameters={
            "database": "customers",
            "environment": "staging",
        }
    )

    narrowed_decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=base_execution_attempt.decision.attempt,
        permitted_effect=permitted_effect,
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-narrowed-001",
        decision=narrowed_decision,
    )

    capability = _make_capability(
        execution_attempt,
    )

    received_effects: list[RequestedEffect] = []

    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            received_effects.append(effect)

            return AdapterExecutionResult(
                result_id="adapter-result-narrowed-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
            )

    adapter = TestAdapter()

    result = adapter.execute(
        execution_attempt=execution_attempt,
        effect=permitted_effect,
        capability=capability,
    )

    assert received_effects == [
        permitted_effect,
    ]

    assert (
        received_effects[0]
        is not execution_attempt
        .consequence
        .action
        .requested_effect
    )

    assert result.execution_attempt is execution_attempt


def test_effect_adapter_execute_returns_adapter_result_only() -> None:
    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            return AdapterExecutionResult(
                result_id="adapter-result-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
                references=[
                    "request-id:123",
                ],
            )

    adapter = TestAdapter()

    execution_attempt = _make_execution_attempt()

    effect = (
        execution_attempt
        .consequence
        .action
        .requested_effect
    )

    capability = _make_capability(
        execution_attempt,
    )

    result = adapter.execute(
        execution_attempt=execution_attempt,
        effect=effect,
        capability=capability,
    )

    assert isinstance(
        result,
        AdapterExecutionResult,
    )

    assert result.execution_attempt is execution_attempt
    assert result.state is AdapterExecutionState.ACKNOWLEDGED

    assert result.references == (
        "request-id:123",
    )

    assert not hasattr(result, "effect")
    assert not hasattr(result, "effect_state")


def test_non_adapter_does_not_satisfy_effect_adapter_protocol() -> None:
    class NotAnAdapter:
        pass

    assert not isinstance(
        NotAnAdapter(),
        EffectAdapter,
    )