import pytest

from cage._facade import CAGE
from cage.config import CAGEConfig
from cage.core.action import RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.capability import ExecutionCapability
from cage.core.custody import (
    AdapterResultMismatchError as CoreAdapterResultMismatchError,
    CapabilityMismatchError,
    CustodyIneligibleError,
)
from cage.core.decision import DecisionState
from cage.core.evaluation import EvaluationOutcome
from cage.core.execution import ExecutionAttempt
from cage.errors import (
    AdapterInvocationError,
    DuplicateExecutionError,
    ExecutionError,
)
from cage.identifiers import EvaluationIds, IdentityKind
from cage.results import (
    ExecutionObservationOrigin,
    ExecutionResult,
)


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[
            tuple[
                ExecutionAttempt,
                RequestedEffect,
                ExecutionCapability,
            ]
        ] = []

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self.calls.append(
            (
                execution_attempt,
                effect,
                capability,
            )
        )

        return AdapterExecutionResult(
            result_id="adapter-result-1",
            execution_attempt=execution_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("provider-receipt-1",),
        )


class RaisingAdapter:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self.calls += 1
        raise self.error


class InvalidReturnAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self.calls += 1
        return None  # type: ignore[return-value]

class MismatchedResultAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.returned_result: AdapterExecutionResult | None = None

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self.calls += 1

        wrong_attempt = ExecutionAttempt(
            execution_attempt_id="execution-attempt-wrong",
            decision=execution_attempt.decision,
        )
        result = AdapterExecutionResult(
            result_id="adapter-result-mismatched",
            execution_attempt=wrong_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("provider-receipt-mismatched",),
        )
        self.returned_result = result
        return result

def test_execute_dispatches_admitted_evaluation_under_custody() -> None:
    def deterministic_id(kind: IdentityKind) -> str:
        return f"{kind.value}-generated"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=deterministic_id),
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()

    result = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )

    assert type(result) is ExecutionResult
    assert result.evaluation is evaluation
    assert result.capability is capability
    assert (
        result.observation_origin
        is ExecutionObservationOrigin.ADAPTER
    )

    assert (
        result.execution_attempt.execution_attempt_id
        == "execution_attempt-generated"
    )
    assert result.execution_attempt.decision is evaluation.decision
    assert result.adapter_result.result_id == "adapter-result-1"
    assert (
        result.adapter_result.state
        is AdapterExecutionState.ACKNOWLEDGED
    )
    assert result.adapter_result.references == (
        "provider-receipt-1",
    )

    assert len(adapter.calls) == 1
    observed_attempt, observed_effect, observed_capability = (
        adapter.calls[0]
    )
    assert observed_attempt is result.execution_attempt
    assert observed_effect is action.requested_effect
    assert observed_capability is capability


def test_execute_preserves_explicit_execution_attempt_id() -> None:
    generated_kinds: list[IdentityKind] = []

    def deterministic_id(kind: IdentityKind) -> str:
        generated_kinds.append(kind)
        return f"{kind.value}-generated"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=deterministic_id),
    )

    action = cage.inputs.action(
        action_id="action-explicit",
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-explicit",
        ids=EvaluationIds(
            consequence_id="consequence-explicit",
            attempt_id="attempt-explicit",
            decision_id="decision-explicit",
            decision_proof_id="decision-proof-explicit",
            warrant_id="warrant-explicit",
        ),
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )

    result = cage.execute(
        evaluation,
        adapter=RecordingAdapter(),
        capability=capability,
        execution_attempt_id="execution-attempt-explicit",
    )

    assert (
        result.execution_attempt.execution_attempt_id
        == "execution-attempt-explicit"
    )
    assert result.adapter_result.result_id == "adapter-result-1"
    assert generated_kinds == [IdentityKind.ADAPTER_RESULT]


def test_execute_does_not_dispatch_refused_evaluation() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.REFUSED
        )
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-refused",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()

    with pytest.raises(
        CustodyIneligibleError,
        match="refused decision is not eligible for custody",
    ):
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    assert adapter.calls == []


def test_execute_rejects_duplicate_dispatch_after_success() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()

    first = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )

    with pytest.raises(DuplicateExecutionError) as captured:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    error = captured.value

    assert len(adapter.calls) == 1
    assert error.execution_attempt is first.execution_attempt
    assert error.consequence_id == evaluation.consequence_id
    assert error.execution is first


def test_execute_releases_reservation_after_capability_mismatch() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    invalid_capability = ExecutionCapability(
        capability_id="capability-invalid",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="different-record",
    )
    valid_capability = ExecutionCapability(
        capability_id="capability-valid",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()

    with pytest.raises(
        CapabilityMismatchError,
        match="capability resource_id does not match",
    ):
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=invalid_capability,
        )

    assert adapter.calls == []

    result = cage.execute(
        evaluation,
        adapter=adapter,
        capability=valid_capability,
    )

    assert result.capability is valid_capability
    assert len(adapter.calls) == 1


def test_execute_replay_does_not_reset_dispatch_guard() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    first_evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=first_evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()

    first_execution = cage.execute(
        first_evaluation,
        adapter=adapter,
        capability=capability,
    )

    replay_evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
        previous=first_evaluation,
    )

    with pytest.raises(DuplicateExecutionError) as captured:
        cage.execute(
            replay_evaluation,
            adapter=adapter,
            capability=capability,
        )

    error = captured.value

    assert replay_evaluation.attempt is not first_evaluation.attempt
    assert (
        replay_evaluation.consequence
        is first_evaluation.consequence
    )
    assert len(adapter.calls) == 1
    assert (
        error.execution_attempt
        is first_execution.execution_attempt
    )
    assert error.execution is first_execution


def test_execute_adapter_exception_retains_recovery_context() -> None:
    counters: dict[IdentityKind, int] = {}

    def sequential_id(kind: IdentityKind) -> str:
        counters[kind] = counters.get(kind, 0) + 1
        return f"{kind.value}-{counters[kind]}"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=sequential_id),
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    provider_error = RuntimeError("provider unavailable")
    adapter = RaisingAdapter(provider_error)

    with pytest.raises(AdapterInvocationError) as captured:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    error = captured.value
    recovery = error.execution

    assert error.__cause__ is provider_error
    assert adapter.calls == 1
    assert recovery.evaluation is evaluation
    assert recovery.capability is capability
    assert (
        recovery.observation_origin
        is ExecutionObservationOrigin.SDK_RECOVERY
    )
    assert (
        recovery.adapter_result.state
        is AdapterExecutionState.UNKNOWN
    )
    assert (
        recovery.adapter_result.result_id
        == "adapter_result-1"
    )
    assert recovery.adapter_result.references == (
        "urn:cage:sdk:recovery-observation",
    )
    assert (
        recovery.adapter_result.execution_attempt
        is recovery.execution_attempt
    )

    with pytest.raises(DuplicateExecutionError) as duplicate:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    assert adapter.calls == 1
    assert (
        duplicate.value.execution_attempt
        is recovery.execution_attempt
    )
    assert duplicate.value.execution is recovery


def test_execute_invalid_adapter_return_retains_recovery_context() -> None:
    counters: dict[IdentityKind, int] = {}

    def sequential_id(kind: IdentityKind) -> str:
        counters[kind] = counters.get(kind, 0) + 1
        return f"{kind.value}-{counters[kind]}"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=sequential_id),
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-invalid-return",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = InvalidReturnAdapter()

    with pytest.raises(ExecutionError) as captured:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    error = captured.value
    recovery = error.execution

    assert type(error).__name__ == "AdapterContractError"
    assert adapter.calls == 1
    assert recovery.evaluation is evaluation
    assert recovery.capability is capability
    assert (
        recovery.observation_origin
        is ExecutionObservationOrigin.SDK_RECOVERY
    )
    assert (
        recovery.adapter_result.state
        is AdapterExecutionState.UNKNOWN
    )
    assert recovery.adapter_result.result_id == "adapter_result-1"
    assert recovery.adapter_result.references == (
        "urn:cage:sdk:recovery-observation",
    )
    assert (
        recovery.adapter_result.execution_attempt
        is recovery.execution_attempt
    )

    with pytest.raises(DuplicateExecutionError) as duplicate:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    assert adapter.calls == 1
    assert (
        duplicate.value.execution_attempt
        is recovery.execution_attempt
    )
    assert duplicate.value.execution is recovery

def test_execute_mismatched_adapter_result_retains_recovery_context() -> None:
    counters: dict[IdentityKind, int] = {}

    def sequential_id(kind: IdentityKind) -> str:
        counters[kind] = counters.get(kind, 0) + 1
        return f"{kind.value}-{counters[kind]}"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=sequential_id),
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="delete-account-mismatched-result",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = MismatchedResultAdapter()

    with pytest.raises(ExecutionError) as captured:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    error = captured.value
    recovery = error.execution

    assert type(error).__name__ == "AdapterResultMismatchError"
    assert isinstance(error, CoreAdapterResultMismatchError)
    assert isinstance(error.__cause__, CoreAdapterResultMismatchError)

    assert adapter.calls == 1
    assert adapter.returned_result is not None
    assert (
        adapter.returned_result.result_id
        == "adapter-result-mismatched"
    )
    assert (
        adapter.returned_result.execution_attempt.execution_attempt_id
        == "execution-attempt-wrong"
    )

    assert recovery.evaluation is evaluation
    assert recovery.capability is capability
    assert (
        recovery.observation_origin
        is ExecutionObservationOrigin.SDK_RECOVERY
    )
    assert (
        recovery.adapter_result.state
        is AdapterExecutionState.UNKNOWN
    )
    assert recovery.adapter_result.result_id == "adapter_result-1"
    assert recovery.adapter_result.references == (
        "urn:cage:sdk:recovery-observation",
    )
    assert (
        recovery.adapter_result.execution_attempt
        is recovery.execution_attempt
    )
    assert (
        recovery.execution_attempt
        is not adapter.returned_result.execution_attempt
    )

    with pytest.raises(DuplicateExecutionError) as duplicate:
        cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )

    assert adapter.calls == 1
    assert (
        duplicate.value.execution_attempt
        is recovery.execution_attempt
    )
    assert duplicate.value.execution is recovery
