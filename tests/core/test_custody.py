import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
from cage.core.consequence import Consequence
from cage.core.custody import (
    AdapterResultMismatchError,
    CapabilityMismatchError,
    CustodyIneligibleError,
    execute_under_custody,
    select_effect_for_custody,
    validate_capability_for_custody,
)
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource


def _make_attempt() -> Attempt:
    action = Action(
        action_id="action-001",
        action_type="access.grant",
        principal=Principal(
            principal_id="principal-123",
        ),
        agent=Agent(
            agent_id="agent-456",
        ),
        resource=Resource(
            resource_id="account-789",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "role": "global-admin",
                "duration_minutes": 480,
            }
        ),
    )

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="access-grant-global-admin",
        action=action,
    )

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def _make_admitted_execution_attempt() -> ExecutionAttempt:
    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=_make_attempt(),
    )

    return ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )


def _make_matching_capability(
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


def test_admitted_decision_selects_original_requested_effect() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    selected = select_effect_for_custody(decision)

    assert (
        selected
        is attempt.consequence.action.requested_effect
    )


def test_narrowed_decision_selects_only_permitted_effect() -> None:
    attempt = _make_attempt()

    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted_effect,
    )

    selected = select_effect_for_custody(decision)

    assert selected is permitted_effect

    assert (
        selected
        is not attempt.consequence.action.requested_effect
    )

    assert selected.parameters["role"] == "scoped-operator"
    assert selected.parameters["duration_minutes"] == 30


@pytest.mark.parametrize(
    "state",
    [
        DecisionState.HELD,
        DecisionState.ESCALATED,
        DecisionState.REFUSED,
    ],
)
def test_ineligible_decisions_cannot_enter_custody(
    state: DecisionState,
) -> None:
    decision = Decision(
        decision_id=f"decision-{state.value}-001",
        state=state,
        attempt=_make_attempt(),
    )

    with pytest.raises(
        CustodyIneligibleError,
        match=f"{state.value} decision is not eligible for custody",
    ):
        select_effect_for_custody(decision)


def test_select_effect_for_custody_requires_decision() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a Decision",
    ):
        select_effect_for_custody(
            "decision-001",  # type: ignore[arg-type]
        )


def test_narrowed_original_effect_remains_preserved() -> None:
    attempt = _make_attempt()

    original_effect = attempt.consequence.action.requested_effect

    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted_effect,
    )

    selected = select_effect_for_custody(decision)

    assert selected is permitted_effect

    assert (
        original_effect.parameters["role"]
        == "global-admin"
    )
    assert (
        original_effect.parameters["duration_minutes"]
        == 480
    )


def test_matching_capability_is_valid_for_custody() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id=attempt.consequence.consequence_id,
        action_type=attempt.consequence.action.action_type,
        resource_id=(
            attempt.consequence.action.resource.resource_id
        ),
    )

    validate_capability_for_custody(
        decision=decision,
        capability=capability,
    )


def test_capability_rejects_wrong_consequence() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-999",
        action_type=attempt.consequence.action.action_type,
        resource_id=(
            attempt.consequence.action.resource.resource_id
        ),
    )

    with pytest.raises(
        CapabilityMismatchError,
        match=(
            "capability consequence_id does not match "
            "decision consequence"
        ),
    ):
        validate_capability_for_custody(
            decision=decision,
            capability=capability,
        )


def test_capability_rejects_wrong_action_type() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id=attempt.consequence.consequence_id,
        action_type="payment.release",
        resource_id=(
            attempt.consequence.action.resource.resource_id
        ),
    )

    with pytest.raises(
        CapabilityMismatchError,
        match=(
            "capability action_type does not match "
            "decision action"
        ),
    ):
        validate_capability_for_custody(
            decision=decision,
            capability=capability,
        )


def test_capability_rejects_wrong_resource() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id=attempt.consequence.consequence_id,
        action_type=attempt.consequence.action.action_type,
        resource_id="account-999",
    )

    with pytest.raises(
        CapabilityMismatchError,
        match=(
            "capability resource_id does not match "
            "decision resource"
        ),
    ):
        validate_capability_for_custody(
            decision=decision,
            capability=capability,
        )


def test_validate_capability_requires_decision() -> None:
    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-001",
        action_type="access.grant",
        resource_id="account-789",
    )

    with pytest.raises(
        TypeError,
        match="decision must be a Decision",
    ):
        validate_capability_for_custody(
            decision="decision-001",  # type: ignore[arg-type]
            capability=capability,
        )


def test_validate_capability_requires_execution_capability() -> None:
    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=_make_attempt(),
    )

    with pytest.raises(
        TypeError,
        match="capability must be an ExecutionCapability",
    ):
        validate_capability_for_custody(
            decision=decision,
            capability="capability-001",  # type: ignore[arg-type]
        )


def test_execute_under_custody_invokes_adapter_with_exact_inputs() -> None:
    execution_attempt = _make_admitted_execution_attempt()
    capability = _make_matching_capability(execution_attempt)

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
            )

    result = execute_under_custody(
        execution_attempt=execution_attempt,
        capability=capability,
        adapter=TestAdapter(),
    )

    assert received["execution_attempt"] is execution_attempt

    assert (
        received["effect"]
        is execution_attempt
        .consequence
        .action
        .requested_effect
    )

    assert received["capability"] is capability

    assert isinstance(result, AdapterExecutionResult)
    assert result.execution_attempt is execution_attempt


def test_execute_under_custody_uses_narrowed_effect_only() -> None:
    attempt = _make_attempt()

    original_effect = attempt.consequence.action.requested_effect

    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted_effect,
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-narrowed-001",
        decision=decision,
    )

    capability = _make_matching_capability(
        execution_attempt
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

    execute_under_custody(
        execution_attempt=execution_attempt,
        capability=capability,
        adapter=TestAdapter(),
    )

    assert received_effects == [permitted_effect]
    assert received_effects[0] is permitted_effect
    assert received_effects[0] is not original_effect


@pytest.mark.parametrize(
    "state",
    [
        DecisionState.HELD,
        DecisionState.ESCALATED,
        DecisionState.REFUSED,
    ],
)
def test_ineligible_decision_never_invokes_adapter(
    state: DecisionState,
) -> None:
    decision = Decision(
        decision_id=f"decision-{state.value}-001",
        state=state,
        attempt=_make_attempt(),
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id=f"execution-attempt-{state.value}-001",
        decision=decision,
    )

    capability = _make_matching_capability(
        execution_attempt
    )

    called = False

    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            nonlocal called
            called = True

            return AdapterExecutionResult(
                result_id="adapter-result-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
            )

    with pytest.raises(CustodyIneligibleError):
        execute_under_custody(
            execution_attempt=execution_attempt,
            capability=capability,
            adapter=TestAdapter(),
        )

    assert called is False


def test_mismatched_capability_never_invokes_adapter() -> None:
    execution_attempt = _make_admitted_execution_attempt()

    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-999",
        action_type=(
            execution_attempt.consequence.action.action_type
        ),
        resource_id=(
            execution_attempt
            .consequence
            .action
            .resource
            .resource_id
        ),
    )

    called = False

    class TestAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            nonlocal called
            called = True

            return AdapterExecutionResult(
                result_id="adapter-result-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
            )

    with pytest.raises(CapabilityMismatchError):
        execute_under_custody(
            execution_attempt=execution_attempt,
            capability=capability,
            adapter=TestAdapter(),
        )

    assert called is False


def test_execute_under_custody_requires_execution_attempt() -> None:
    execution_attempt = _make_admitted_execution_attempt()
    capability = _make_matching_capability(execution_attempt)

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

    with pytest.raises(
        TypeError,
        match="execution_attempt must be an ExecutionAttempt",
    ):
        execute_under_custody(
            execution_attempt="execution-attempt-001",  # type: ignore[arg-type]
            capability=capability,
            adapter=TestAdapter(),
        )


def test_execute_under_custody_requires_effect_adapter() -> None:
    execution_attempt = _make_admitted_execution_attempt()
    capability = _make_matching_capability(execution_attempt)

    with pytest.raises(
        TypeError,
        match="adapter must satisfy EffectAdapter",
    ):
        execute_under_custody(
            execution_attempt=execution_attempt,
            capability=capability,
            adapter=object(),  # type: ignore[arg-type]
        )


def test_execute_under_custody_requires_adapter_result() -> None:
    execution_attempt = _make_admitted_execution_attempt()
    capability = _make_matching_capability(execution_attempt)

    class BadAdapter:
        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> object:
            return object()

    with pytest.raises(
        TypeError,
        match="adapter must return an AdapterExecutionResult",
    ):
        execute_under_custody(
            execution_attempt=execution_attempt,
            capability=capability,
            adapter=BadAdapter(),  # type: ignore[arg-type]
        )


def test_adapter_result_must_match_execution_attempt() -> None:
    execution_attempt = _make_admitted_execution_attempt()
    capability = _make_matching_capability(execution_attempt)

    different_execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-999",
        decision=execution_attempt.decision,
    )

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
                execution_attempt=different_execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
            )

    with pytest.raises(
        AdapterResultMismatchError,
        match=(
            "adapter result execution_attempt does not match "
            "custody execution_attempt"
        ),
    ):
        execute_under_custody(
            execution_attempt=execution_attempt,
            capability=capability,
            adapter=TestAdapter(),
        )