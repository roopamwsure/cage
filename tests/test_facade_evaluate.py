from cage._facade import CAGE
from cage.config import CAGEConfig
from cage.core.attempt import Attempt
from cage.core.decision import DecisionState
from cage.core.evaluation import EvaluationOutcome
from cage.identifiers import EvaluationIds, IdentityKind
from cage.results import EvaluationResult


def test_evaluate_builds_decision_only_assurance_lineage() -> None:
    observed: dict[str, object] = {}

    def deterministic_id(kind: IdentityKind) -> str:
        return f"{kind.value}-generated"

    def rule(
        attempt,
        evidence,
        standing,
        delegations,
        approvals,
        context,
    ) -> EvaluationOutcome:
        observed["attempt"] = attempt
        observed["evidence"] = evidence
        observed["standing"] = standing
        observed["delegations"] = delegations
        observed["approvals"] = approvals
        observed["context"] = context
        return EvaluationOutcome(state=DecisionState.ADMITTED)

    cage = CAGE(
        rule=rule,
        config=CAGEConfig(id_factory=deterministic_id),
    )

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"table": "accounts", "record_id": 1},
    )
    evidence = cage.inputs.evidence(
        evidence_type="change.ticket",
        subject="database.delete",
        source="change-management",
        data={"ticket": "CHG-1"},
    )
    standing = cage.inputs.standing(
        standing_type="employment",
        subject="principal-1",
        source="identity-directory",
        attributes={"active": True},
    )
    delegation = cage.inputs.delegation(
        delegator="principal-1",
        delegatee="agent-1",
        source="delegation-service",
        scope={"action_type": "database.delete"},
    )
    approval = cage.inputs.approval(
        approval_type="human.review",
        approver="reviewer-1",
        subject="database.delete",
        source="approval-service",
        scope={"resource_id": "record-1"},
    )
    context = cage.inputs.context(
        context_type="request.environment",
        source="application",
        values={"environment": "production"},
    )

    result = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
        evidence=(evidence,),
        standing=(standing,),
        delegations=(delegation,),
        approvals=(approval,),
        context=(context,),
    )

    assert type(result) is EvaluationResult
    assert result.consequence.consequence_id == "consequence-generated"
    assert result.consequence.idempotency_key == "delete-account-1"
    assert result.consequence.action is action
    assert result.attempt.attempt_id == "attempt-generated"
    assert result.attempt.previous_attempt_id is None
    assert result.decision.decision_id == "decision-generated"
    assert result.decision.state is DecisionState.ADMITTED
    assert result.decision.permitted_effect is None

    assert result.decision_proof.proof_id == "decision_proof-generated"
    assert result.decision_proof.evidence_refs == ("evidence-generated",)
    assert result.decision_proof.standing_refs == ("standing-generated",)
    assert result.decision_proof.delegation_refs == (
        "delegation-generated",
    )
    assert result.decision_proof.approval_refs == ("approval-generated",)
    assert result.decision_proof.context_refs == ("context-generated",)

    assert result.warrant.warrant_id == "warrant-generated"
    assert result.warrant.schema_version == "0.7"
    assert result.warrant.effect_proof is None
    assert result.warrant.previous_warrant_id is None

    assert type(observed["attempt"]) is Attempt
    assert observed["attempt"] is result.attempt
    assert observed["evidence"] == (evidence,)
    assert observed["standing"] == (standing,)
    assert observed["delegations"] == (delegation,)
    assert observed["approvals"] == (approval,)
    assert observed["context"] == (context,)

def test_evaluate_preserves_explicit_lifecycle_ids() -> None:
    def unexpected_factory(kind: IdentityKind) -> str:
        raise AssertionError(
            f"factory must not be called for {kind.value}"
        )

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.REFUSED
        ),
        config=CAGEConfig(id_factory=unexpected_factory),
    )

    action = cage.inputs.action(
        action_id="action-explicit",
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )

    result = cage.evaluate(
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

    assert result.consequence_id == "consequence-explicit"
    assert result.attempt.attempt_id == "attempt-explicit"
    assert result.decision.decision_id == "decision-explicit"
    assert result.decision.state is DecisionState.REFUSED
    assert result.decision_proof.proof_id == "decision-proof-explicit"
    assert result.warrant.warrant_id == "warrant-explicit"
def test_evaluate_reuses_equivalent_canonical_consequence() -> None:
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

    first = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )
    second = cage.evaluate(
        action=action,
        idempotency_key="delete-account-1",
    )

    assert second.consequence is first.consequence
    assert second.consequence_id == first.consequence_id
    assert second.attempt is not first.attempt
    assert second.attempt.attempt_id != first.attempt.attempt_id
    assert second.decision.decision_id != first.decision.decision_id
    assert second.warrant.warrant_id != first.warrant.warrant_id
