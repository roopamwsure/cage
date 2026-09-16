import pytest

from cage.core.effect import EffectState
from cage.core.action import Action, RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
)
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt
from cage.core.identity import Agent, Principal, Resource
from cage.core.verification import (
    EffectVerificationResult,
    VerificationState,
)


def _make_execution_attempt() -> ExecutionAttempt:
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

    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    return ExecutionAttempt(
        execution_attempt_id="execution-attempt-001",
        decision=decision,
    )


def _make_adapter_result(
    *,
    state: AdapterExecutionState = (
        AdapterExecutionState.ACKNOWLEDGED
    ),
) -> AdapterExecutionResult:
    return AdapterExecutionResult(
        result_id="adapter-result-001",
        execution_attempt=_make_execution_attempt(),
        state=state,
        references=[
            "request-id:123",
        ],
    )


def test_verified_bound_records_authoritative_verification() -> None:
    adapter_result = _make_adapter_result()

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.VERIFIED_BOUND,
        references=[
            "authoritative-record:456",
        ],
    )

    assert verification.verification_id == "verification-001"
    assert verification.adapter_result is adapter_result
    assert verification.state is VerificationState.VERIFIED_BOUND

    assert verification.references == (
        "authoritative-record:456",
    )


def test_verified_no_bind_records_authoritative_verification() -> None:
    adapter_result = _make_adapter_result(
        state=AdapterExecutionState.ERROR,
    )

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.VERIFIED_NO_BIND,
        references=[
            "authoritative-query:789",
        ],
    )

    assert verification.state is VerificationState.VERIFIED_NO_BIND

    assert verification.references == (
        "authoritative-query:789",
    )


def test_inconclusive_allows_no_verification_references() -> None:
    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=_make_adapter_result(
            state=AdapterExecutionState.UNKNOWN,
        ),
        state=VerificationState.INCONCLUSIVE,
    )

    assert verification.state is VerificationState.INCONCLUSIVE
    assert verification.references == ()


@pytest.mark.parametrize(
    "state",
    [
        VerificationState.VERIFIED_BOUND,
        VerificationState.VERIFIED_NO_BIND,
    ],
)
def test_conclusive_verification_requires_references(
    state: VerificationState,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"{state.value} requires verification references",
    ):
        EffectVerificationResult(
            verification_id="verification-001",
            adapter_result=_make_adapter_result(),
            state=state,
        )


def test_verification_references_are_frozen() -> None:
    references = [
        "authoritative-record:456",
    ]

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=_make_adapter_result(),
        state=VerificationState.VERIFIED_BOUND,
        references=references,
    )

    references.append(
        "authoritative-record:999",
    )

    assert verification.references == (
        "authoritative-record:456",
    )


def test_verification_rejects_blank_reference() -> None:
    with pytest.raises(
        ValueError,
        match="references must not be empty",
    ):
        EffectVerificationResult(
            verification_id="verification-001",
            adapter_result=_make_adapter_result(),
            state=VerificationState.VERIFIED_BOUND,
            references=[
                "   ",
            ],
        )


def test_verification_requires_non_empty_identity() -> None:
    with pytest.raises(
        ValueError,
        match="verification_id must not be empty",
    ):
        EffectVerificationResult(
            verification_id="   ",
            adapter_result=_make_adapter_result(),
            state=VerificationState.INCONCLUSIVE,
        )


def test_verification_requires_adapter_execution_result() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "adapter_result must be an "
            "AdapterExecutionResult"
        ),
    ):
        EffectVerificationResult(
            verification_id="verification-001",
            adapter_result="adapter-result-001",  # type: ignore[arg-type]
            state=VerificationState.INCONCLUSIVE,
        )


def test_verification_requires_verification_state() -> None:
    with pytest.raises(
        TypeError,
        match="state must be a VerificationState",
    ):
        EffectVerificationResult(
            verification_id="verification-001",
            adapter_result=_make_adapter_result(),
            state="verified_bound",  # type: ignore[arg-type]
            references=[
                "authoritative-record:456",
            ],
        )


def test_verification_preserves_execution_attempt_lineage() -> None:
    adapter_result = _make_adapter_result()

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.INCONCLUSIVE,
    )

    assert (
        verification.execution_attempt
        is adapter_result.execution_attempt
    )


def test_verification_preserves_consequence_lineage() -> None:
    adapter_result = _make_adapter_result()

    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=adapter_result,
        state=VerificationState.INCONCLUSIVE,
    )

    assert (
        verification.consequence
        is adapter_result
        .execution_attempt
        .consequence
    )


@pytest.mark.parametrize(
    "adapter_state",
    [
        AdapterExecutionState.ACKNOWLEDGED,
        AdapterExecutionState.REJECTED,
        AdapterExecutionState.ERROR,
        AdapterExecutionState.UNKNOWN,
    ],
)
def test_adapter_state_does_not_determine_verification_state(
    adapter_state: AdapterExecutionState,
) -> None:
    adapter_result = _make_adapter_result(
        state=adapter_state,
    )

    verification = EffectVerificationResult(
        verification_id=f"verification-{adapter_state.value}",
        adapter_result=adapter_result,
        state=VerificationState.INCONCLUSIVE,
    )

    assert verification.adapter_result.state is adapter_state
    assert verification.state is VerificationState.INCONCLUSIVE

def test_verified_bound_creates_bound_effect() -> None:
    verification = EffectVerificationResult(
        verification_id="verification-bound-001",
        adapter_result=_make_adapter_result(
            state=AdapterExecutionState.ACKNOWLEDGED,
        ),
        state=VerificationState.VERIFIED_BOUND,
        references=[
            "authoritative-record:bound-123",
        ],
    )

    from cage.core.verification import create_effect_from_verification

    effect = create_effect_from_verification(
        effect_id="effect-001",
        verification=verification,
    )

    assert effect.effect_id == "effect-001"
    assert effect.state is EffectState.BOUND
    assert effect.consequence is verification.consequence

    assert effect.verification_refs == (
        "authoritative-record:bound-123",
    )


def test_verified_no_bind_creates_no_bind_effect() -> None:
    verification = EffectVerificationResult(
        verification_id="verification-no-bind-001",
        adapter_result=_make_adapter_result(
            state=AdapterExecutionState.ERROR,
        ),
        state=VerificationState.VERIFIED_NO_BIND,
        references=[
            "authoritative-record:no-bind-123",
        ],
    )

    from cage.core.verification import create_effect_from_verification

    effect = create_effect_from_verification(
        effect_id="effect-002",
        verification=verification,
    )

    assert effect.state is EffectState.NO_BIND
    assert effect.consequence is verification.consequence

    assert effect.verification_refs == (
        "authoritative-record:no-bind-123",
    )


def test_inconclusive_creates_effect_unknown() -> None:
    verification = EffectVerificationResult(
        verification_id="verification-inconclusive-001",
        adapter_result=_make_adapter_result(
            state=AdapterExecutionState.UNKNOWN,
        ),
        state=VerificationState.INCONCLUSIVE,
    )

    from cage.core.verification import create_effect_from_verification

    effect = create_effect_from_verification(
        effect_id="effect-003",
        verification=verification,
    )

    assert effect.state is EffectState.EFFECT_UNKNOWN
    assert effect.consequence is verification.consequence
    assert effect.verification_refs == ()


@pytest.mark.parametrize(
    (
        "adapter_state",
        "verification_state",
        "expected_effect_state",
        "references",
    ),
    [
        (
            AdapterExecutionState.ACKNOWLEDGED,
            VerificationState.INCONCLUSIVE,
            EffectState.EFFECT_UNKNOWN,
            (),
        ),
        (
            AdapterExecutionState.ERROR,
            VerificationState.VERIFIED_BOUND,
            EffectState.BOUND,
            ("authoritative-record:bound",),
        ),
        (
            AdapterExecutionState.REJECTED,
            VerificationState.VERIFIED_BOUND,
            EffectState.BOUND,
            ("authoritative-record:bound",),
        ),
        (
            AdapterExecutionState.ACKNOWLEDGED,
            VerificationState.VERIFIED_NO_BIND,
            EffectState.NO_BIND,
            ("authoritative-record:no-bind",),
        ),
        (
            AdapterExecutionState.UNKNOWN,
            VerificationState.VERIFIED_NO_BIND,
            EffectState.NO_BIND,
            ("authoritative-record:no-bind",),
        ),
    ],
)
def test_adapter_state_does_not_control_final_effect_state(
    adapter_state: AdapterExecutionState,
    verification_state: VerificationState,
    expected_effect_state: EffectState,
    references: tuple[str, ...],
) -> None:
    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=_make_adapter_result(
            state=adapter_state,
        ),
        state=verification_state,
        references=references,
    )

    from cage.core.verification import create_effect_from_verification

    effect = create_effect_from_verification(
        effect_id="effect-001",
        verification=verification,
    )

    assert verification.adapter_result.state is adapter_state
    assert verification.state is verification_state
    assert effect.state is expected_effect_state


def test_effect_preserves_verified_consequence_identity() -> None:
    verification = EffectVerificationResult(
        verification_id="verification-001",
        adapter_result=_make_adapter_result(),
        state=VerificationState.VERIFIED_BOUND,
        references=[
            "authoritative-record:456",
        ],
    )

    from cage.core.verification import create_effect_from_verification

    effect = create_effect_from_verification(
        effect_id="effect-001",
        verification=verification,
    )

    assert (
        effect.consequence.consequence_id
        == verification.consequence.consequence_id
    )

    assert effect.consequence is verification.consequence


def test_create_effect_requires_verification_result() -> None:
    from cage.core.verification import create_effect_from_verification

    with pytest.raises(
        TypeError,
        match="verification must be an EffectVerificationResult",
    ):
        create_effect_from_verification(
            effect_id="effect-001",
            verification="verification-001",  # type: ignore[arg-type]
        )    