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
from cage.core.warrant import DecisionProof, Warrant
from cage.errors import CAGETypeError, CAGEValueError
from cage.results import (
    EvaluationResult,
    ExecutionObservationOrigin,
    ExecutionResult,
)


def _evaluation_result() -> EvaluationResult:
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
    warrant = Warrant(
        warrant_id="warrant-1",
        schema_version="0.7",
        decision_proof=DecisionProof(
            proof_id="decision-proof-1",
            decision=decision,
        ),
    )
    return EvaluationResult(warrant=warrant)


def _execution_parts(
    evaluation: EvaluationResult,
) -> tuple[ExecutionCapability, AdapterExecutionResult]:
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type=evaluation.consequence.action.action_type,
        resource_id=evaluation.consequence.action.resource.resource_id,
    )
    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-1",
        decision=evaluation.decision,
    )
    adapter_result = AdapterExecutionResult(
        result_id="adapter-result-1",
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
        references=("provider-receipt-1",),
    )
    return capability, adapter_result


def test_execution_observation_origin_has_documented_values() -> None:
    assert {
        origin.name: origin.value for origin in ExecutionObservationOrigin
    } == {
        "ADAPTER": "adapter",
        "SDK_RECOVERY": "sdk_recovery",
    }


def test_execution_result_exposes_execution_lineage() -> None:
    evaluation = _evaluation_result()
    capability, adapter_result = _execution_parts(evaluation)

    result = ExecutionResult(
        evaluation=evaluation,
        capability=capability,
        adapter_result=adapter_result,
        observation_origin=ExecutionObservationOrigin.ADAPTER,
    )

    assert result.evaluation is evaluation
    assert result.capability is capability
    assert result.adapter_result is adapter_result
    assert result.observation_origin is ExecutionObservationOrigin.ADAPTER
    assert result.decision is evaluation.decision
    assert result.decision_proof is evaluation.decision_proof
    assert result.execution_attempt is adapter_result.execution_attempt
    assert result.consequence_id == "consequence-1"
    assert result.idempotency_key == "delete-account-1"
    assert not hasattr(result, "effect")


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "message"),
    [
        ("evaluation", object(), "evaluation must be an EvaluationResult"),
        (
            "capability",
            object(),
            "capability must be an ExecutionCapability",
        ),
        (
            "adapter_result",
            object(),
            "adapter_result must be an AdapterExecutionResult",
        ),
        (
            "observation_origin",
            "adapter",
            "observation_origin must be an ExecutionObservationOrigin",
        ),
    ],
)
def test_execution_result_rejects_invalid_field_types(
    field_name: str,
    invalid_value: object,
    message: str,
) -> None:
    evaluation = _evaluation_result()
    capability, adapter_result = _execution_parts(evaluation)
    arguments: dict[str, object] = {
        "evaluation": evaluation,
        "capability": capability,
        "adapter_result": adapter_result,
        "observation_origin": ExecutionObservationOrigin.ADAPTER,
    }
    arguments[field_name] = invalid_value

    with pytest.raises(CAGETypeError, match=message):
        ExecutionResult(**arguments)  # type: ignore[arg-type]


def test_execution_result_rejects_mismatched_decision_lineage() -> None:
    evaluation = _evaluation_result()
    capability, _ = _execution_parts(evaluation)

    other_attempt = Attempt(
        attempt_id="attempt-other",
        consequence=evaluation.consequence,
    )
    other_decision = Decision(
        decision_id="decision-other",
        state=DecisionState.ADMITTED,
        attempt=other_attempt,
    )
    adapter_result = AdapterExecutionResult(
        result_id="adapter-result-other",
        execution_attempt=ExecutionAttempt(
            execution_attempt_id="execution-attempt-other",
            decision=other_decision,
        ),
        state=AdapterExecutionState.ACKNOWLEDGED,
    )

    with pytest.raises(
        CAGEValueError,
        match="adapter result decision does not match evaluation decision",
    ):
        ExecutionResult(
            evaluation=evaluation,
            capability=capability,
            adapter_result=adapter_result,
            observation_origin=ExecutionObservationOrigin.ADAPTER,
        )


def test_execution_result_rejects_mismatched_capability_scope() -> None:
    evaluation = _evaluation_result()
    _, adapter_result = _execution_parts(evaluation)
    capability = ExecutionCapability(
        capability_id="capability-wrong",
        consequence_id="consequence-other",
        action_type=evaluation.consequence.action.action_type,
        resource_id=evaluation.consequence.action.resource.resource_id,
    )

    with pytest.raises(
        CAGEValueError,
        match="capability does not match evaluation decision",
    ):
        ExecutionResult(
            evaluation=evaluation,
            capability=capability,
            adapter_result=adapter_result,
            observation_origin=ExecutionObservationOrigin.ADAPTER,
        )


def test_execution_result_is_immutable() -> None:
    evaluation = _evaluation_result()
    capability, adapter_result = _execution_parts(evaluation)
    result = ExecutionResult(
        evaluation=evaluation,
        capability=capability,
        adapter_result=adapter_result,
        observation_origin=ExecutionObservationOrigin.ADAPTER,
    )

    with pytest.raises(FrozenInstanceError):
        result.observation_origin = ExecutionObservationOrigin.SDK_RECOVERY