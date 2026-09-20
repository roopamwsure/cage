from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.identity import Agent, Principal, Resource
from cage.core.warrant import DecisionProof, Warrant
from cage.errors import CAGETypeError, CAGEValueError
from cage.results import EvaluationResult


def _decision_only_warrant() -> Warrant:
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
        evidence_refs=("evidence-1",),
        context_refs=("context-1",),
    )
    return Warrant(
        warrant_id="warrant-1",
        schema_version="0.7",
        decision_proof=decision_proof,
    )


def test_evaluation_result_exposes_decision_lineage() -> None:
    warrant = _decision_only_warrant()

    result = EvaluationResult(warrant=warrant)

    assert result.warrant is warrant
    assert result.decision_proof is warrant.decision_proof
    assert result.decision is warrant.decision_proof.decision
    assert result.attempt is warrant.decision_proof.decision.attempt
    assert result.consequence is result.attempt.consequence
    assert result.consequence_id == "consequence-1"
    assert result.idempotency_key == "delete-account-1"


def test_evaluation_result_requires_warrant() -> None:
    with pytest.raises(CAGETypeError, match="warrant must be a Warrant"):
        EvaluationResult(warrant=object())  # type: ignore[arg-type]


def test_evaluation_result_rejects_warrant_with_effect_proof() -> None:
    warrant = _decision_only_warrant()

    # Simulate a Warrant carrying assurance-stage content. EvaluationResult
    # must reject it before exposing it as a decision-only result.
    object.__setattr__(warrant, "effect_proof", object())

    with pytest.raises(
        CAGEValueError,
        match="EvaluationResult requires a decision-only Warrant",
    ):
        EvaluationResult(warrant=warrant)


def test_evaluation_result_is_immutable() -> None:
    result = EvaluationResult(warrant=_decision_only_warrant())

    with pytest.raises(FrozenInstanceError):
        result.warrant = _decision_only_warrant()