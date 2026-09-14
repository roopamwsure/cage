import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import DecisionState
from cage.core.evaluation import EvaluationOutcome, evaluate_attempt
from cage.core.identity import Agent, Principal, Resource


def _make_attempt() -> Attempt:
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

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def test_admitted_outcome() -> None:
    outcome = EvaluationOutcome(
        state=DecisionState.ADMITTED,
    )

    assert outcome.state is DecisionState.ADMITTED
    assert outcome.permitted_effect is None


def test_narrowed_outcome_requires_permitted_effect() -> None:
    with pytest.raises(
        ValueError,
        match="NARROWED outcomes require a permitted_effect",
    ):
        EvaluationOutcome(
            state=DecisionState.NARROWED,
        )


def test_narrowed_outcome_accepts_permitted_effect() -> None:
    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        },
    )

    outcome = EvaluationOutcome(
        state=DecisionState.NARROWED,
        permitted_effect=permitted_effect,
    )

    assert outcome.state is DecisionState.NARROWED
    assert outcome.permitted_effect is permitted_effect


def test_non_narrowed_outcome_rejects_permitted_effect() -> None:
    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
        },
    )

    with pytest.raises(
        ValueError,
        match="permitted_effect is only valid for NARROWED outcomes",
    ):
        EvaluationOutcome(
            state=DecisionState.ADMITTED,
            permitted_effect=permitted_effect,
        )


def test_outcome_rejects_invalid_state() -> None:
    with pytest.raises(
        TypeError,
        match="state must be a DecisionState",
    ):
        EvaluationOutcome(
            state="admitted",  # type: ignore[arg-type]
        )


def test_evaluate_attempt_creates_decision_from_rule() -> None:
    attempt = _make_attempt()

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        assert received_attempt is attempt
        assert evidence == ()
        assert standing == ()
        assert delegations == ()
        assert approvals == ()
        assert context == ()

        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    decision = evaluate_attempt(
        decision_id="decision-001",
        attempt=attempt,
        rule=rule,
    )

    assert decision.decision_id == "decision-001"
    assert decision.state is DecisionState.ADMITTED
    assert decision.attempt is attempt
    assert decision.permitted_effect is None


def test_evaluate_attempt_preserves_narrowed_effect() -> None:
    attempt = _make_attempt()

    permitted_effect = RequestedEffect(
        parameters={
            "database": "customers",
            "environment": "staging",
        },
    )

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            state=DecisionState.NARROWED,
            permitted_effect=permitted_effect,
        )

    decision = evaluate_attempt(
        decision_id="decision-002",
        attempt=attempt,
        rule=rule,
    )

    assert decision.state is DecisionState.NARROWED
    assert decision.permitted_effect is permitted_effect


def test_evaluate_attempt_passes_assurance_inputs_to_rule() -> None:
    attempt = _make_attempt()

    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="provider-policy-result",
        subject="principal-123",
        source="provider",
        data={
            "result": "allow",
        },
    )

    standing = Standing(
        standing_id="standing-001",
        standing_type="employment",
        subject="principal-123",
        source="directory",
        attributes={
            "status": "active",
        },
    )

    delegation = Delegation(
        delegation_id="delegation-001",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-service",
        scope={
            "action_type": "database.delete",
        },
    )

    approval = Approval(
        approval_id="approval-001",
        approval_type="human",
        approver="manager-123",
        subject="consequence-001",
        source="approval-service",
        scope={
            "environment": "production",
        },
    )

    context_item = Context(
        context_id="context-001",
        context_type="runtime",
        source="runtime-service",
        values={
            "environment": "production",
        },
    )

    def rule(
        received_attempt: Attempt,
        received_evidence: tuple[Evidence, ...],
        received_standing: tuple[Standing, ...],
        received_delegations: tuple[Delegation, ...],
        received_approvals: tuple[Approval, ...],
        received_context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        assert received_attempt is attempt
        assert received_evidence == (evidence,)
        assert received_standing == (standing,)
        assert received_delegations == (delegation,)
        assert received_approvals == (approval,)
        assert received_context == (context_item,)

        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    decision = evaluate_attempt(
        decision_id="decision-003",
        attempt=attempt,
        rule=rule,
        evidence=[evidence],
        standing=[standing],
        delegations=[delegation],
        approvals=[approval],
        context=[context_item],
    )

    assert decision.state is DecisionState.ADMITTED


def test_evaluate_attempt_freezes_assurance_collections() -> None:
    attempt = _make_attempt()

    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="provider-policy-result",
        subject="principal-123",
        source="provider",
        data={
            "result": "allow",
        },
    )

    def rule(
        received_attempt: Attempt,
        received_evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        assert isinstance(received_evidence, tuple)
        assert received_evidence == (evidence,)

        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    evaluate_attempt(
        decision_id="decision-004",
        attempt=attempt,
        rule=rule,
        evidence=[evidence],
    )


def test_evaluate_attempt_requires_non_empty_decision_id() -> None:
    attempt = _make_attempt()

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    with pytest.raises(
        ValueError,
        match="decision_id must not be empty",
    ):
        evaluate_attempt(
            decision_id="   ",
            attempt=attempt,
            rule=rule,
        )


def test_evaluate_attempt_rejects_invalid_attempt() -> None:
    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    with pytest.raises(
        TypeError,
        match="attempt must be an Attempt",
    ):
        evaluate_attempt(
            decision_id="decision-001",
            attempt="attempt-001",  # type: ignore[arg-type]
            rule=rule,
        )


def test_evaluate_attempt_rejects_non_callable_rule() -> None:
    attempt = _make_attempt()

    with pytest.raises(
        TypeError,
        match="rule must be callable",
    ):
        evaluate_attempt(
            decision_id="decision-001",
            attempt=attempt,
            rule="admit",  # type: ignore[arg-type]
        )


def test_evaluate_attempt_rejects_rule_returning_none() -> None:
    attempt = _make_attempt()

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> None:
        return None

    with pytest.raises(
        TypeError,
        match="rule must return an EvaluationOutcome",
    ):
        evaluate_attempt(
            decision_id="decision-001",
            attempt=attempt,
            rule=rule,  # type: ignore[arg-type]
        )


def test_evaluate_attempt_rejects_invalid_rule_result() -> None:
    attempt = _make_attempt()

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> DecisionState:
        return DecisionState.ADMITTED

    with pytest.raises(
        TypeError,
        match="rule must return an EvaluationOutcome",
    ):
        evaluate_attempt(
            decision_id="decision-001",
            attempt=attempt,
            rule=rule,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        (
            "evidence",
            ["invalid"],
            "evidence must contain only Evidence",
        ),
        (
            "standing",
            ["invalid"],
            "standing must contain only Standing",
        ),
        (
            "delegations",
            ["invalid"],
            "delegations must contain only Delegation",
        ),
        (
            "approvals",
            ["invalid"],
            "approvals must contain only Approval",
        ),
        (
            "context",
            ["invalid"],
            "context must contain only Context",
        ),
    ],
)
def test_evaluate_attempt_rejects_invalid_assurance_items(
    field_name: str,
    value: object,
    message: str,
) -> None:
    attempt = _make_attempt()

    def rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    values = {
        "decision_id": "decision-001",
        "attempt": attempt,
        "rule": rule,
    }

    values[field_name] = value

    with pytest.raises(
        TypeError,
        match=message,
    ):
        evaluate_attempt(**values)  # type: ignore[arg-type]