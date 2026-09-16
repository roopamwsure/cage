import pytest

from cage.core.evaluation import EvaluationOutcome, evaluate_attempt
from cage.core.action import Action, RequestedEffect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.replay import create_replay_attempt
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.effect import Effect, EffectState
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource
from cage.core.warrant import (
    DecisionProof,
    EffectProof,
    Warrant,
    create_decision_proof,
    create_effect_proof,
)
from cage.core.capability import ExecutionCapability
from cage.core.custody import execute_under_custody
from cage.core.verification import (
    EffectVerificationResult,
    VerificationState,
    create_effect_from_verification,
    reconcile_effect_verification,
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


def _make_verification_for_effect(
    effect: Effect,
    *,
    verification_id: str = "verification-001",
    execution_attempt_id: str = "execution-attempt-001",
    adapter_result_id: str = "adapter-result-001",
) -> EffectVerificationResult:
    decision = _make_decision_for_consequence(
        effect.consequence
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id=execution_attempt_id,
        decision=decision,
    )

    adapter_result = AdapterExecutionResult(
        result_id=adapter_result_id,
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
        references=[
            "request-id:123",
        ],
    )

    if effect.state is EffectState.BOUND:
        verification_state = VerificationState.VERIFIED_BOUND

    elif effect.state is EffectState.NO_BIND:
        verification_state = VerificationState.VERIFIED_NO_BIND

    else:
        verification_state = VerificationState.INCONCLUSIVE

    return EffectVerificationResult(
        verification_id=verification_id,
        adapter_result=adapter_result,
        state=verification_state,
        references=effect.verification_refs,
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

    verification = _make_verification_for_effect(effect)

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
    )

    assert effect_proof.effect is effect
    assert effect_proof.verification is verification
    assert effect_proof.effect.state is EffectState.BOUND
    assert (
        effect_proof.effect.consequence.consequence_id
        == "consequence-001"
    )
    assert effect_proof.verification_id == "verification-001"
    assert effect_proof.adapter_result_id == "adapter-result-001"
    assert (
        effect_proof.execution_attempt_id
        == "execution-attempt-001"
    )


def test_effect_proof_can_preserve_explicit_uncertainty() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    verification = _make_verification_for_effect(effect)

    proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
    )

    assert proof.effect.state is EffectState.EFFECT_UNKNOWN
    assert proof.verification.state is VerificationState.INCONCLUSIVE


def test_decision_proof_requires_decision() -> None:
    with pytest.raises(TypeError):
        DecisionProof(
            proof_id="decision-proof-001",
            decision="admitted",
        )


def test_effect_proof_requires_effect() -> None:
    valid_effect = Effect(
        effect_id="effect-valid-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    verification = _make_verification_for_effect(
        valid_effect
    )

    with pytest.raises(
        TypeError,
        match="effect must be an Effect",
    ):
        EffectProof(
            proof_id="effect-proof-001",
            effect="bound",  # type: ignore[arg-type]
            verification=verification,
        )



def test_effect_proof_requires_verification_result() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    with pytest.raises(
        TypeError,
        match=(
            "verification must be an "
            "EffectVerificationResult"
        ),
    ):
        EffectProof(
            proof_id="effect-proof-001",
            effect=effect,
            verification="verification-001",  # type: ignore[arg-type]
        )


def test_effect_proof_rejects_mismatched_effect_state() -> None:
    consequence = _make_consequence()

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=consequence,
        verification_refs=[
            "authoritative-record:123",
        ],
    )

    decision = _make_decision_for_consequence(
        consequence
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )

    adapter_result = AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
    )

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.VERIFIED_NO_BIND,
        references=[
            "authoritative-record:123",
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "effect state does not match "
            "verification state"
        ),
    ):
        EffectProof(
            proof_id="effect-proof-001",
            effect=effect,
            verification=verification,
        )


def test_effect_proof_rejects_mismatched_verification_references() -> None:
    consequence = _make_consequence()

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=consequence,
        verification_refs=[
            "authoritative-record:effect",
        ],
    )

    decision = _make_decision_for_consequence(
        consequence
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )

    adapter_result = AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.ACKNOWLEDGED,
    )

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.VERIFIED_BOUND,
        references=[
            "authoritative-record:verification",
        ],
    )

    with pytest.raises(
        ValueError,
        match=(
            "effect verification_refs do not match "
            "verification references"
        ),
    ):
        EffectProof(
            proof_id="effect-proof-001",
            effect=effect,
            verification=verification,
        )


def test_effect_proof_rejects_different_verification_consequence() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
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

    different_effect = Effect(
        effect_id="effect-999",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=different_consequence,
    )

    verification = _make_verification_for_effect(
        different_effect,
        verification_id="verification-999",
        execution_attempt_id="execution-attempt-999",
        adapter_result_id="adapter-result-999",
    )

    with pytest.raises(
        ValueError,
        match=(
            "effect and verification must refer "
            "to the same consequence"
        ),
    ):
        EffectProof(
            proof_id="effect-proof-001",
            effect=effect,
            verification=verification,
        )


def test_create_effect_proof_preserves_verified_lineage() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=_make_consequence(),
        verification_refs=[
            "authoritative-record:123",
        ],
    )

    verification = _make_verification_for_effect(
        effect
    )

    proof = create_effect_proof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
    )

    assert proof.effect is effect
    assert proof.verification is verification
    assert proof.verification_id == "verification-001"
    assert proof.adapter_result_id == "adapter-result-001"
    assert (
        proof.execution_attempt_id
        == "execution-attempt-001"
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

    verification = _make_verification_for_effect(effect)

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
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
    assert warrant.execution_attempt_id == "execution-attempt-001"
    assert warrant.adapter_result_id == "adapter-result-001"
    assert warrant.verification_id == "verification-001"


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

    verification = _make_verification_for_effect(effect)

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
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

    verification = _make_verification_for_effect(
        effect,
        verification_id="verification-999",
        execution_attempt_id="execution-attempt-999",
        adapter_result_id="adapter-result-999",
    )

    effect_proof = EffectProof(
        proof_id="effect-proof-999",
        effect=effect,
        verification=verification,
    )

    with pytest.raises(
        ValueError,
        match=(
            "decision proof and effect proof must refer "
            "to the same consequence"
        ),
    ):
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
            verification=_make_verification_for_effect(
                unknown_effect
            ),
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

    verification = _make_verification_for_effect(effect)

    effect_proof = EffectProof(
        proof_id="effect-proof-001",
        effect=effect,
        verification=verification,
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
            verification=_make_verification_for_effect(
                effect
            ),
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

def test_end_to_end_pre_effect_assurance_path() -> None:
    consequence = _make_consequence()

    attempt = Attempt(
        attempt_id="attempt-e2e-001",
        consequence=consequence,
    )

    evidence = Evidence(
        evidence_id="evidence-e2e-001",
        evidence_type="provider-policy-result",
        subject="consequence-001",
        source="provider-policy-service",
        data={
            "result": "allow",
        },
    )

    standing = Standing(
        standing_id="standing-e2e-001",
        standing_type="employment",
        subject="principal-123",
        source="directory-service",
        attributes={
            "status": "active",
        },
    )

    delegation = Delegation(
        delegation_id="delegation-e2e-001",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-service",
        scope={
            "action_type": "database.delete",
        },
    )

    approval = Approval(
        approval_id="approval-e2e-001",
        approval_type="human",
        approver="database-owner",
        subject="consequence-001",
        source="approval-service",
        scope={
            "environment": "production",
        },
    )

    context_item = Context(
        context_id="context-e2e-001",
        context_type="runtime",
        source="runtime-service",
        values={
            "maintenance_window": True,
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
        decision_id="decision-e2e-001",
        attempt=attempt,
        rule=rule,
        evidence=[evidence],
        standing=[standing],
        delegations=[delegation],
        approvals=[approval],
        context=[context_item],
    )

    decision_proof = create_decision_proof(
        proof_id="decision-proof-e2e-001",
        decision=decision,
        evidence=[evidence],
        standing=[standing],
        delegations=[delegation],
        approvals=[approval],
        context=[context_item],
    )

    warrant = Warrant(
        warrant_id="warrant-e2e-001",
        schema_version="0.5-draft",
        decision_proof=decision_proof,
    )

    assert decision.state is DecisionState.ADMITTED

    assert decision_proof.evidence_refs == (
        "evidence-e2e-001",
    )
    assert decision_proof.standing_refs == (
        "standing-e2e-001",
    )
    assert decision_proof.delegation_refs == (
        "delegation-e2e-001",
    )
    assert decision_proof.approval_refs == (
        "approval-e2e-001",
    )
    assert decision_proof.context_refs == (
        "context-e2e-001",
    )

    assert warrant.consequence_id == "consequence-001"
    assert warrant.action_id == "action-001"
    assert warrant.attempt_id == "attempt-e2e-001"

    assert warrant.effect_proof is None

def test_replay_preserves_consequence_and_creates_new_decision_lineage() -> None:
    consequence = _make_consequence()

    first_attempt = Attempt(
        attempt_id="attempt-replay-001",
        consequence=consequence,
    )

    def first_rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        assert received_attempt is first_attempt

        return EvaluationOutcome(
            state=DecisionState.ESCALATED,
        )

    first_decision = evaluate_attempt(
        decision_id="decision-replay-001",
        attempt=first_attempt,
        rule=first_rule,
    )

    second_attempt = create_replay_attempt(
        previous_attempt=first_attempt,
        attempt_id="attempt-replay-002",
    )

    approval = Approval(
        approval_id="approval-replay-001",
        approval_type="human",
        approver="database-owner",
        subject=consequence.consequence_id,
        source="approval-service",
        scope={
            "database": "customers",
            "environment": "production",
        },
    )

    def second_rule(
        received_attempt: Attempt,
        evidence: tuple[Evidence, ...],
        standing: tuple[Standing, ...],
        delegations: tuple[Delegation, ...],
        approvals: tuple[Approval, ...],
        context: tuple[Context, ...],
    ) -> EvaluationOutcome:
        assert received_attempt is second_attempt
        assert approvals == (approval,)

        return EvaluationOutcome(
            state=DecisionState.ADMITTED,
        )

    second_decision = evaluate_attempt(
        decision_id="decision-replay-002",
        attempt=second_attempt,
        rule=second_rule,
        approvals=[approval],
    )

    first_proof = create_decision_proof(
        proof_id="decision-proof-replay-001",
        decision=first_decision,
    )

    second_proof = create_decision_proof(
        proof_id="decision-proof-replay-002",
        decision=second_decision,
        approvals=[approval],
    )

    first_warrant = Warrant(
        warrant_id="warrant-replay-001",
        schema_version="0.5-draft",
        decision_proof=first_proof,
    )

    second_warrant = Warrant(
        warrant_id="warrant-replay-002",
        schema_version="0.5-draft",
        decision_proof=second_proof,
        previous_warrant_id=first_warrant.warrant_id,
    )

    assert first_attempt.consequence is consequence
    assert second_attempt.consequence is consequence

    assert second_attempt.attempt_id != first_attempt.attempt_id
    assert (
        second_attempt.previous_attempt_id
        == first_attempt.attempt_id
    )

    assert first_decision.attempt is first_attempt
    assert second_decision.attempt is second_attempt

    assert first_decision.state is DecisionState.ESCALATED
    assert second_decision.state is DecisionState.ADMITTED

    assert (
        first_warrant.consequence_id
        == second_warrant.consequence_id
    )
    assert (
        second_warrant.previous_warrant_id
        == first_warrant.warrant_id
    )

    assert second_warrant.effect_proof is None

def test_end_to_end_v06_custody_warrant_lineage() -> None:
    consequence = _make_consequence()

    attempt = Attempt(
        attempt_id="attempt-v06-001",
        consequence=consequence,
    )
    decision = Decision(
        decision_id="decision-v06-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    decision_proof = create_decision_proof(
        proof_id="decision-proof-v06-001",
        decision=decision,
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-v06-001",
        decision=decision,
    )

    capability = ExecutionCapability(
        capability_id="capability-v06-001",
        consequence_id=consequence.consequence_id,
        action_type=consequence.action.action_type,
        resource_id=consequence.action.resource.resource_id,
    )

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
                result_id="adapter-result-v06-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
                references=[
                    "request-id:v06-123",
                ],
            )

    adapter_result = execute_under_custody(
        execution_attempt=execution_attempt,
        capability=capability,
        adapter=TestAdapter(),
    )

    assert received["execution_attempt"] is execution_attempt
    assert (
        received["effect"]
        is consequence.action.requested_effect
    )
    assert received["capability"] is capability

    verification = EffectVerificationResult(
        verification_id="verification-v06-001",
        adapter_result=adapter_result,
        state=VerificationState.VERIFIED_BOUND,
        references=[
            "authoritative-record:v06-456",
        ],
    )

    effect = create_effect_from_verification(
        effect_id="effect-v06-001",
        verification=verification,
    )

    effect_proof = create_effect_proof(
        proof_id="effect-proof-v06-001",
        effect=effect,
        verification=verification,
    )

    warrant = Warrant(
        warrant_id="warrant-v06-001",
        schema_version="0.6-draft",
        decision_proof=decision_proof,
        effect_proof=effect_proof,
    )

    assert warrant.consequence_id == consequence.consequence_id
    assert warrant.action_id == consequence.action.action_id
    assert warrant.attempt_id == attempt.attempt_id

    assert (
        warrant.execution_attempt_id
        == "execution-attempt-v06-001"
    )

    assert (
        warrant.adapter_result_id
        == "adapter-result-v06-001"
    )

    assert (
        warrant.verification_id
        == "verification-v06-001"
    )

    assert warrant.effect_proof is effect_proof
    assert effect_proof.effect is effect
    assert effect_proof.verification is verification

    assert effect.state is EffectState.BOUND

    assert effect.verification_refs == (
        "authoritative-record:v06-456",
    )

    assert (
        effect.consequence
        is decision.attempt.consequence
    )


def test_end_to_end_v06_reconciliation_warrant_lineage() -> None:
    consequence = _make_consequence()

    attempt = Attempt(
        attempt_id="attempt-v06-reconcile-001",
        consequence=consequence,
    )

    decision = Decision(
        decision_id="decision-v06-reconcile-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    decision_proof = create_decision_proof(
        proof_id="decision-proof-v06-reconcile-001",
        decision=decision,
    )

    execution_attempt = ExecutionAttempt(
        execution_attempt_id="execution-attempt-v06-reconcile-001",
        decision=decision,
    )

    capability = ExecutionCapability(
        capability_id="capability-v06-reconcile-001",
        consequence_id=consequence.consequence_id,
        action_type=consequence.action.action_type,
        resource_id=consequence.action.resource.resource_id,
    )

    class CountingAdapter:
        def __init__(self) -> None:
            self.call_count = 0

        def execute(
            self,
            *,
            execution_attempt: ExecutionAttempt,
            effect: RequestedEffect,
            capability: ExecutionCapability,
        ) -> AdapterExecutionResult:
            self.call_count += 1

            return AdapterExecutionResult(
                result_id="adapter-result-v06-reconcile-001",
                execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
                references=[
                    "request-id:v06-reconcile-123",
                ],
            )

    adapter = CountingAdapter()

    adapter_result = execute_under_custody(
        execution_attempt=execution_attempt,
        capability=capability,
        adapter=adapter,
    )

    assert adapter.call_count == 1

    first_verification = EffectVerificationResult(
        verification_id="verification-v06-reconcile-001",
        adapter_result=adapter_result,
        state=VerificationState.INCONCLUSIVE,
    )

    first_effect = create_effect_from_verification(
        effect_id="effect-v06-reconcile-001",
        verification=first_verification,
    )

    first_effect_proof = create_effect_proof(
        proof_id="effect-proof-v06-reconcile-001",
        effect=first_effect,
        verification=first_verification,
    )

    first_warrant = Warrant(
        warrant_id="warrant-v06-reconcile-001",
        schema_version="0.6-draft",
        decision_proof=decision_proof,
        effect_proof=first_effect_proof,
    )

    assert first_effect.state is EffectState.EFFECT_UNKNOWN
    assert first_effect.verification_refs == ()

    assert first_warrant.consequence_id == consequence.consequence_id
    assert first_warrant.attempt_id == attempt.attempt_id

    assert (
        first_warrant.execution_attempt_id
        == execution_attempt.execution_attempt_id
    )

    assert (
        first_warrant.adapter_result_id
        == adapter_result.result_id
    )

    assert (
        first_warrant.verification_id
        == first_verification.verification_id
    )

    assert first_warrant.previous_warrant_id is None

    class ReconciliationVerifier:
        def __init__(self) -> None:
            self.call_count = 0

        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            self.call_count += 1

            return EffectVerificationResult(
                verification_id="verification-v06-reconcile-002",
                adapter_result=adapter_result,
                state=VerificationState.VERIFIED_BOUND,
                references=[
                    "authoritative-record:v06-reconcile-456",
                ],
            )

    verifier = ReconciliationVerifier()

    second_verification = reconcile_effect_verification(
        adapter_result=adapter_result,
        verifier=verifier,
    )

    assert verifier.call_count == 1

    second_effect = create_effect_from_verification(
        effect_id="effect-v06-reconcile-002",
        verification=second_verification,
    )

    second_effect_proof = create_effect_proof(
        proof_id="effect-proof-v06-reconcile-002",
        effect=second_effect,
        verification=second_verification,
    )

    second_warrant = Warrant(
        warrant_id="warrant-v06-reconcile-002",
        schema_version="0.6-draft",
        decision_proof=decision_proof,
        effect_proof=second_effect_proof,
        previous_warrant_id=first_warrant.warrant_id,
    )

    assert adapter.call_count == 1

    assert (
        first_verification.adapter_result
        is adapter_result
    )

    assert (
        second_verification.adapter_result
        is adapter_result
    )

    assert (
        first_verification.execution_attempt
        is execution_attempt
    )

    assert (
        second_verification.execution_attempt
        is execution_attempt
    )

    assert (
        first_effect.consequence
        is consequence
    )

    assert (
        second_effect.consequence
        is consequence
    )

    assert first_effect.state is EffectState.EFFECT_UNKNOWN
    assert second_effect.state is EffectState.BOUND

    assert (
        second_effect.verification_refs
        == (
            "authoritative-record:v06-reconcile-456",
        )
    )

    assert (
        first_warrant.consequence_id
        == second_warrant.consequence_id
        == consequence.consequence_id
    )

    assert (
        first_warrant.attempt_id
        == second_warrant.attempt_id
        == attempt.attempt_id
    )

    assert (
        first_warrant.execution_attempt_id
        == second_warrant.execution_attempt_id
        == execution_attempt.execution_attempt_id
    )

    assert (
        first_warrant.adapter_result_id
        == second_warrant.adapter_result_id
        == adapter_result.result_id
    )

    assert (
        first_warrant.verification_id
        != second_warrant.verification_id
    )

    assert (
        second_warrant.previous_warrant_id
        == first_warrant.warrant_id
    )

    assert (
        second_warrant.decision_proof
        is first_warrant.decision_proof
    )

    assert first_effect is not second_effect
    assert first_effect_proof is not second_effect_proof
    assert first_warrant is not second_warrant

    assert adapter.call_count == 1
