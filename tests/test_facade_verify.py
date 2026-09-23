import pytest

from cage._facade import CAGE
from cage.config import CAGEConfig
from cage.core.action import RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.capability import ExecutionCapability
from cage.core.decision import DecisionState
from cage.core.effect import EffectState
from cage.core.evaluation import EvaluationOutcome
from cage.core.execution import ExecutionAttempt
from cage.core.verification import (
    EffectVerificationResult,
    VerificationState,
)
from cage.errors import (
    CAGETypeError,
    IdentifierGenerationError,
    VerifierInvocationError,
)
from cage.identifiers import AssuranceIds, IdentityKind
from cage.results import ExecutionObservationOrigin


class AcknowledgingAdapter:
    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        return AdapterExecutionResult(
            result_id="adapter-result-1",
            execution_attempt=execution_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("provider-receipt-1",),
        )


class BoundVerifier:
    def __init__(self) -> None:
        self.calls: list[AdapterExecutionResult] = []

    def verify(
        self,
        *,
        adapter_result: AdapterExecutionResult,
    ) -> EffectVerificationResult:
        self.calls.append(adapter_result)

        return EffectVerificationResult(
            verification_id="verification-1",
            adapter_result=adapter_result,
            state=VerificationState.VERIFIED_BOUND,
            references=("provider-observation-1",),
        )


def test_verify_creates_bound_assurance_result() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(
            id_factory=lambda kind: f"{kind.value}-generated"
        ),
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
        idempotency_key="delete-account-verify-bound",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )
    verifier = BoundVerifier()

    assurance = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="assurance-warrant-1",
        ),
    )

    assert verifier.calls == [execution.adapter_result]
    assert assurance.execution is execution
    assert (
        assurance.observation_origin
        is ExecutionObservationOrigin.ADAPTER
    )

    assert assurance.verification.verification_id == "verification-1"
    assert (
        assurance.verification.state
        is VerificationState.VERIFIED_BOUND
    )
    assert assurance.verification.references == (
        "provider-observation-1",
    )

    assert assurance.effect.effect_id == "effect-1"
    assert assurance.effect.state is EffectState.BOUND
    assert assurance.effect.verification_refs == (
        "provider-observation-1",
    )

    assert assurance.effect_proof.proof_id == "effect-proof-1"
    assert assurance.warrant.warrant_id == "assurance-warrant-1"
    assert (
        assurance.warrant.previous_warrant_id
        == evaluation.warrant.warrant_id
    )
    assert assurance.decision_proof is evaluation.decision_proof
    assert assurance.adapter_result is execution.adapter_result


@pytest.mark.parametrize(
    (
        "verification_state",
        "references",
        "expected_effect_state",
    ),
    [
        (
            VerificationState.VERIFIED_NO_BIND,
            ("provider-observation-no-bind",),
            EffectState.NO_BIND,
        ),
        (
            VerificationState.INCONCLUSIVE,
            (),
            EffectState.EFFECT_UNKNOWN,
        ),
    ],
)
def test_verify_maps_verification_state_to_effect(
    verification_state: VerificationState,
    references: tuple[str, ...],
    expected_effect_state: EffectState,
) -> None:
    class StateVerifier:
        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            return EffectVerificationResult(
                verification_id="verification-state-1",
                adapter_result=adapter_result,
                state=verification_state,
                references=references,
            )

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(
            id_factory=lambda kind: f"{kind.value}-generated"
        ),
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
        idempotency_key=(
            f"delete-account-{verification_state.value}"
        ),
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )

    assurance = cage.verify(
        execution,
        verifier=StateVerifier(),
        ids=AssuranceIds(
            effect_id="effect-state-1",
            effect_proof_id="effect-proof-state-1",
            warrant_id="assurance-warrant-state-1",
        ),
    )

    assert assurance.verification.state is verification_state
    assert assurance.verification.references == references
    assert assurance.effect.state is expected_effect_state
    assert assurance.effect.verification_refs == references
    assert assurance.execution is execution


def test_verify_generates_assurance_identifiers() -> None:
    counters: dict[IdentityKind, int] = {}
    generated_kinds: list[IdentityKind] = []

    def sequential_id(kind: IdentityKind) -> str:
        generated_kinds.append(kind)
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
        idempotency_key="delete-account-generated-assurance-ids",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )

    generated_kinds.clear()

    assurance = cage.verify(
        execution,
        verifier=BoundVerifier(),
    )

    assert generated_kinds == [
        IdentityKind.EFFECT,
        IdentityKind.EFFECT_PROOF,
        IdentityKind.WARRANT,
    ]
    assert assurance.effect.effect_id == "effect-1"
    assert assurance.effect_proof.proof_id == "effect_proof-1"
    assert assurance.warrant.warrant_id == "warrant-2"


def test_verify_explicit_ids_bypass_generation() -> None:
    generated_kinds: list[IdentityKind] = []

    def tracking_id(kind: IdentityKind) -> str:
        generated_kinds.append(kind)
        return f"{kind.value}-generated"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=tracking_id),
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
        idempotency_key="delete-account-explicit-assurance-ids",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )

    generated_kinds.clear()

    assurance = cage.verify(
        execution,
        verifier=BoundVerifier(),
        ids=AssuranceIds(
            effect_id="effect-explicit",
            effect_proof_id="effect-proof-explicit",
            warrant_id="warrant-explicit",
        ),
    )

    assert generated_kinds == []
    assert assurance.effect.effect_id == "effect-explicit"
    assert assurance.effect_proof.proof_id == (
        "effect-proof-explicit"
    )
    assert assurance.warrant.warrant_id == "warrant-explicit"


def test_verify_id_generation_failure_precedes_verifier() -> None:
    def failing_id(kind: IdentityKind) -> str:
        if kind is IdentityKind.EFFECT:
            raise RuntimeError(
                "effect ID generation failed"
            )

        return f"{kind.value}-generated"

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        ),
        config=CAGEConfig(id_factory=failing_id),
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
        idempotency_key="delete-account-assurance-id-failure",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )
    verifier = BoundVerifier()

    with pytest.raises(IdentifierGenerationError) as captured:
        cage.verify(
            execution,
            verifier=verifier,
        )

    assert captured.value.kind is IdentityKind.EFFECT
    assert isinstance(captured.value.__cause__, RuntimeError)
    assert str(captured.value.__cause__) == (
        "effect ID generation failed"
    )
    assert verifier.calls == []

def test_verify_rejects_invalid_verifier() -> None:
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
        idempotency_key="delete-account-invalid-verifier",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )

    with pytest.raises(
        CAGETypeError,
        match="verifier must satisfy EffectVerifier",
    ):
        cage.verify(
            execution,
            verifier=object(),  # type: ignore[arg-type]
            ids=AssuranceIds(
                effect_id="effect-1",
                effect_proof_id="effect-proof-1",
                warrant_id="warrant-1",
            ),
        )


def test_verify_wraps_verifier_invocation_failure() -> None:
    class RaisingVerifier:
        def __init__(self) -> None:
            self.calls = 0
            self.error = RuntimeError(
                "verification provider unavailable"
            )

        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            self.calls += 1
            raise self.error

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
        idempotency_key="delete-account-verifier-failure",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    execution = cage.execute(
        evaluation,
        adapter=AcknowledgingAdapter(),
        capability=capability,
    )
    verifier = RaisingVerifier()

    with pytest.raises(VerifierInvocationError) as captured:
        cage.verify(
            execution,
            verifier=verifier,
            ids=AssuranceIds(
                effect_id="effect-verifier-failure",
                effect_proof_id="effect-proof-verifier-failure",
                warrant_id="warrant-verifier-failure",
            ),
        )

    assert verifier.calls == 1
    assert captured.value.execution is execution
    assert captured.value.__cause__ is verifier.error
    assert str(captured.value) == (
        "effect verifier invocation failed"
    )
