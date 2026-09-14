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
from cage.core.decision import Decision, DecisionState
from cage.core.effect import Effect, EffectState
from cage.core.identity import Agent, Principal, Resource
from cage.core.warrant import (
    DecisionProof,
    EffectProof,
    Warrant,
    create_decision_proof,
)


def _make_consequence() -> Consequence:
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

    return Consequence(
        consequence_id="consequence-001",
        idempotency_key="delete-customers-production",
        action=action,
    )


def _make_attempt() -> Attempt:
    return Attempt(
        attempt_id="attempt-001",
        consequence=_make_consequence(),
    )


def _make_decision() -> Decision:
    return Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=_make_attempt(),
    )


def _make_decision_for_consequence(
    consequence: Consequence,
) -> Decision:
    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    return Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )


def test_decision_proof_records_assurance_references() -> None:
    proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=_make_decision(),
        evidence_refs=["evidence-001"],
        standing_refs=["standing-001"],
        delegation_refs=["delegation-001"],
        approval_refs=["approval-001"],
        context_refs=["context-001"],
    )

    assert proof.decision.state is DecisionState.ADMITTED
    assert proof.evidence_refs == ("evidence-001",)
    assert proof.approval_refs == ("approval-001",)


def test_decision_proof_references_are_immutable() -> None:
    references = ["evidence-001"]

    proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=_make_decision(),
        evidence_refs=references,
    )

    references.append("evidence-002")

    assert proof.evidence_refs == ("evidence-001",)


def test_decision_proof_rejects_blank_reference() -> None:
    with pytest.raises(ValueError):
        DecisionProof(
            proof_id="decision-proof-001",
            decision=_make_decision(),
            evidence_refs=["   "],
        )


def test_effect_proof_wraps_effect_assertion() -> None:
    consequence = _make_consequence()

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=consequence,
        verification_refs=[
            "target-system:deletion-confirmation-123"
        ],
    )

    proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
    )

    assert proof.effect.state is EffectState.BOUND
    assert (
        proof.effect.consequence.consequence_id
        == "consequence-001"
    )


def test_effect_proof_can_preserve_explicit_uncertainty() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
    )

    assert proof.effect.state is EffectState.EFFECT_UNKNOWN


def test_decision_proof_requires_decision() -> None:
    with pytest.raises(TypeError):
        DecisionProof(
            proof_id="decision-proof-001",
            decision="admitted",
        )


def test_effect_proof_requires_effect() -> None:
    with pytest.raises(TypeError):
        EffectProof(
            proof_id="effect-proof-001",
            effect="bound",
        )


def test_warrant_can_exist_before_effect_proof() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
    )

    assert warrant.effect_proof is None
    assert warrant.consequence_id == "consequence-001"
    assert warrant.action_id == "action-001"
    assert warrant.attempt_id == "attempt-001"


def test_warrant_combines_decision_and_effect_proofs() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
        evidence_refs=["evidence-001"],
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=consequence,
        verification_refs=[
            "target-system:deletion-confirmation-123"
        ],
    )

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        effect_proof=effect_proof,
    )

    assert (
        warrant.decision_proof.decision.state
        is DecisionState.ADMITTED
    )

    assert (
        warrant.effect_proof.effect.state
        is EffectState.BOUND
    )

    assert warrant.consequence_id == "consequence-001"


def test_warrant_can_preserve_unknown_effect() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=consequence,
    )

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        effect_proof=effect_proof,
    )

    assert (
        warrant.decision_proof.decision.state
        is DecisionState.ADMITTED
    )

    assert (
        warrant.effect_proof.effect.state
        is EffectState.EFFECT_UNKNOWN
    )


def test_warrant_rejects_proofs_for_different_consequences() -> None:
    decision_consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        decision_consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    different_action = Action(
        action_id="action-999",
        action_type="database.delete",
        principal=Principal(
            principal_id="principal-123",
        ),
        agent=Agent(
            agent_id="agent-456",
        ),
        resource=Resource(
            resource_id="database-999",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "database": "payroll",
                "environment": "production",
            }
        ),
    )

    different_consequence = Consequence(
        consequence_id="consequence-999",
        idempotency_key="delete-payroll-production",
        action=different_action,
    )

    effect = Effect(
        effect_id="effect-999",
        state=EffectState.BOUND,
        consequence=different_consequence,
        verification_refs=[
            "target-system:confirmation-999"
        ],
    )

    effect_proof = EffectProof(
        proof_id="effect-proof-999",
        effect=effect,
    )

    with pytest.raises(ValueError):
        Warrant(
            warrant_id="warrant-001",
            schema_version="0.5-draft",
            decision_proof=decision_proof,
            effect_proof=effect_proof,
        )


def test_warrant_can_reference_previous_warrant() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-002",
        decision=decision,
    )

    warrant = Warrant(
        warrant_id="warrant-002",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        previous_warrant_id="warrant-001",
    )

    assert warrant.previous_warrant_id == "warrant-001"


def test_admitted_decision_does_not_create_effect_proof() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
    )

    assert (
        warrant.decision_proof.decision.state
        is DecisionState.ADMITTED
    )

    assert warrant.effect_proof is None


def test_decision_only_warrant_is_distinct_from_unknown_effect() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    without_effect_proof = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
    )

    unknown_effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=consequence,
    )

    with_unknown_effect = Warrant(
        warrant_id="warrant-002",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        effect_proof=EffectProof(
            proof_id="effect-proof-001",
            effect=unknown_effect,
        ),
        previous_warrant_id="warrant-001",
    )

    assert without_effect_proof.effect_proof is None

    assert (
        with_unknown_effect.effect_proof.effect.state
        is EffectState.EFFECT_UNKNOWN
    )


def test_refused_decision_does_not_prove_no_bind() -> None:
    consequence = _make_consequence()

    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.REFUSED,
        attempt=attempt,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=DecisionProof(
            proof_id="decision-proof-001",
            decision=decision,
        ),
    )

    assert (
        warrant.decision_proof.decision.state
        is DecisionState.REFUSED
    )

    assert warrant.effect_proof is None


def test_admitted_decision_and_no_bind_effect_can_coexist() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.NO_BIND,
        consequence=consequence,
        verification_refs=[
            "target-system:no-effect-confirmation-123"
        ],
    )

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
    )

    warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        effect_proof=effect_proof,
    )

    assert (
        warrant.decision_proof.decision.state
        is DecisionState.ADMITTED
    )

    assert (
        warrant.effect_proof.effect.state
        is EffectState.NO_BIND
    )


def test_warrant_update_preserves_consequence_identity() -> None:
    consequence = _make_consequence()

    decision = _make_decision_for_consequence(
        consequence
    )

    decision_proof = DecisionProof(
        proof_id="decision-proof-001",
        decision=decision,
    )

    first_warrant = Warrant(
        warrant_id="warrant-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=consequence,
        verification_refs=[
            "target-system:deletion-confirmation-123"
        ],
    )

    second_warrant = Warrant(
        warrant_id="warrant-002",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
        effect_proof=EffectProof(
            proof_id="effect-proof-001",
            effect=effect,
        ),
        previous_warrant_id=first_warrant.warrant_id,
    )

    assert (
        first_warrant.consequence_id
        == second_warrant.consequence_id
    )

    assert (
        second_warrant.previous_warrant_id
        == first_warrant.warrant_id
    )


def test_create_decision_proof_uses_assurance_input_ids() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-proof-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="risk-assessment",
        subject="consequence-001",
        source="risk-service",
        data={
            "risk_level": "low",
        },
    )

    standing = Standing(
        standing_id="standing-001",
        standing_type="employment",
        subject="principal-123",
        source="directory-service",
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

    proof = create_decision_proof(
        proof_id="proof-001",
        decision=decision,
        evidence=[evidence],
        standing=[standing],
        delegations=[delegation],
        approvals=[approval],
        context=[context_item],
    )

    assert proof.proof_id == "proof-001"
    assert proof.decision is decision
    assert proof.evidence_refs == ("evidence-001",)
    assert proof.standing_refs == ("standing-001",)
    assert proof.delegation_refs == ("delegation-001",)
    assert proof.approval_refs == ("approval-001",)
    assert proof.context_refs == ("context-001",)


def test_create_decision_proof_accepts_empty_assurance_inputs() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-proof-002",
        state=DecisionState.REFUSED,
        attempt=attempt,
    )

    proof = create_decision_proof(
        proof_id="proof-002",
        decision=decision,
    )

    assert proof.decision is decision
    assert proof.evidence_refs == ()
    assert proof.standing_refs == ()
    assert proof.delegation_refs == ()
    assert proof.approval_refs == ()
    assert proof.context_refs == ()


def test_create_decision_proof_preserves_reference_order() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-proof-003",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    evidence_1 = Evidence(
        evidence_id="evidence-001",
        evidence_type="signal",
        subject="consequence-001",
        source="source-a",
        data={
            "value": "one",
        },
    )

    evidence_2 = Evidence(
        evidence_id="evidence-002",
        evidence_type="signal",
        subject="consequence-001",
        source="source-b",
        data={
            "value": "two",
        },
    )

    proof = create_decision_proof(
        proof_id="proof-003",
        decision=decision,
        evidence=[
            evidence_1,
            evidence_2,
        ],
    )

    assert proof.evidence_refs == (
        "evidence-001",
        "evidence-002",
    )