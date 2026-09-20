from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.adapter import AdapterExecutionResult, AdapterExecutionState
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource
from cage.core.verification import (
    EffectVerificationResult,
    VerificationState,
    create_effect_from_verification,
)
from cage.core.warrant import (
    DecisionProof,
    Warrant,
    create_effect_proof,
)
from cage.errors import CAGETypeError, CAGEValueError
from cage.results import (
    AssuranceResult,
    EvaluationResult,
    ExecutionObservationOrigin,
    ExecutionResult,
)


def _execution_result() -> ExecutionResult:
    action = Action(
        action_id="action-1",
        action_type="database.delete",
        principal=Principal(principal_id="principal-1"),
        agent=Agent(agent_id="agent-1"),
        resource=Resource(resource_id="record-1"),
        requested_effect=RequestedEffect(
            parameters={"table": "accounts", "record_id": 1}
        ),
    )
    consequence = Consequence(
        consequence_id="consequence-1",
        idempotency_key="delete-account-1",
        action=action,
    )
    attempt = Attempt(
        attempt_id="attempt-1",
        consequence=consequence,
    )
    decision = Decision(
        decision_id="decision-1",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )
    decision_proof = DecisionProof(
        proof_id="decision-proof-1",
        decision=decision,
    )
    evaluation = EvaluationResult(
        warrant=Warrant(
            warrant_id="warrant-evaluation",
            schema_version="0.7",
            decision_proof=decision_proof,
        )
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=consequence.consequence_id,
        action_type=action.action_type,
        resource_id=action.resource.resource_id,
    )
    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-1",
        decision=decision,
    )
    adapter_result = AdapterExecutionResult(
        result_id="adapter-result-1",
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
        references=("provider-receipt-1",),
    )
    return ExecutionResult(
        evaluation=evaluation,
        capability=capability,
        adapter_result=adapter_result,
        observation_origin=ExecutionObservationOrigin.ADAPTER,
    )


def _assurance_warrant(execution: ExecutionResult) -> Warrant:
    verification = EffectVerificationResult(
        verification_id="verification-1",
        adapter_result=execution.adapter_result,
        state=VerificationState.VERIFIED_BOUND,
        references=("external-record-1",),
    )
    effect = create_effect_from_verification(
        effect_id="effect-1",
        verification=verification,
    )
    effect_proof = create_effect_proof(
        proof_id="effect-proof-1",
        effect=effect,
        verification=verification,
    )
    return Warrant(
        warrant_id="warrant-assurance",
        schema_version="0.7",
        decision_proof=execution.decision_proof,
        effect_proof=effect_proof,
        previous_warrant_id=execution.evaluation.warrant.warrant_id,
    )


def test_assurance_result_exposes_verified_lifecycle() -> None:
    execution = _execution_result()
    warrant = _assurance_warrant(execution)

    result = AssuranceResult(
        execution=execution,
        warrant=warrant,
    )

    assert result.execution is execution
    assert result.warrant is warrant
    assert result.decision is execution.decision
    assert result.decision_proof is execution.decision_proof
    assert result.execution_attempt is execution.execution_attempt
    assert result.adapter_result is execution.adapter_result
    assert (
        result.observation_origin
        is ExecutionObservationOrigin.ADAPTER
    )
    assert result.effect_proof is warrant.effect_proof
    assert result.effect is warrant.effect_proof.effect
    assert result.verification is warrant.effect_proof.verification
    assert result.consequence_id == "consequence-1"
    assert result.idempotency_key == "delete-account-1"


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("execution", object(), "execution must be an ExecutionResult"),
        ("warrant", object(), "warrant must be a Warrant"),
    ],
)
def test_assurance_result_rejects_invalid_field_types(
    field_name: str,
    invalid_value: object,
    message: str,
) -> None:
    execution = _execution_result()
    arguments: dict[str, object] = {
        "execution": execution,
        "warrant": _assurance_warrant(execution),
    }
    arguments[field_name] = invalid_value

    with pytest.raises(CAGETypeError, match=message):
        AssuranceResult(**arguments)  # type: ignore[arg-type]


def test_assurance_result_requires_effect_proof() -> None:
    execution = _execution_result()

    with pytest.raises(
        CAGEValueError,
        match="AssuranceResult requires a Warrant with an EffectProof",
    ):
        AssuranceResult(
            execution=execution,
            warrant=execution.evaluation.warrant,
        )


def test_assurance_result_rejects_mismatched_decision_proof() -> None:
    execution = _execution_result()
    warrant = _assurance_warrant(execution)
    other_decision = Decision(
        decision_id="decision-other",
        state=DecisionState.ADMITTED,
        attempt=execution.decision.attempt,
    )
    mismatched_warrant = Warrant(
        warrant_id="warrant-mismatched-decision",
        schema_version="0.7",
        decision_proof=DecisionProof(
            proof_id="decision-proof-other",
            decision=other_decision,
        ),
        effect_proof=warrant.effect_proof,
        previous_warrant_id=execution.evaluation.warrant.warrant_id,
    )

    with pytest.raises(
        CAGEValueError,
        match="warrant decision proof does not match execution evaluation",
    ):
        AssuranceResult(
            execution=execution,
            warrant=mismatched_warrant,
        )


def test_assurance_result_rejects_mismatched_execution_observation() -> None:
    execution = _execution_result()
    other_execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-other",
        decision=execution.decision,
    )
    other_adapter_result = AdapterExecutionResult(
        result_id="adapter-result-other",
        execution_attempt=other_execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
    )
    verification = EffectVerificationResult(
        verification_id="verification-other",
        adapter_result=other_adapter_result,
        state=VerificationState.INCONCLUSIVE,
    )
    effect = create_effect_from_verification(
        effect_id="effect-other",
        verification=verification,
    )
    mismatched_warrant = Warrant(
        warrant_id="warrant-mismatched-execution",
        schema_version="0.7",
        decision_proof=execution.decision_proof,
        effect_proof=create_effect_proof(
            proof_id="effect-proof-other",
            effect=effect,
            verification=verification,
        ),
        previous_warrant_id=execution.evaluation.warrant.warrant_id,
    )

    with pytest.raises(
        CAGEValueError,
        match="warrant effect proof does not match execution observation",
    ):
        AssuranceResult(
            execution=execution,
            warrant=mismatched_warrant,
        )


def test_assurance_result_is_immutable() -> None:
    execution = _execution_result()
    result = AssuranceResult(
        execution=execution,
        warrant=_assurance_warrant(execution),
    )

    with pytest.raises(FrozenInstanceError):
        result.warrant = execution.evaluation.warrant