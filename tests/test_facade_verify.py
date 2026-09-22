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
from cage.identifiers import AssuranceIds
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
