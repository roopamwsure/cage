from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.consequence import Consequence
from cage.core.effect import Effect, EffectState
from cage.core.identity import Agent, Principal, Resource


def _make_consequence() -> Consequence:
    action = Action(
        action_id="action-001",
        action_type="payment.release",
        principal=Principal(principal_id="principal-123"),
        agent=Agent(agent_id="agent-456"),
        resource=Resource(resource_id="payment-system-789"),
        requested_effect=RequestedEffect(
            parameters={
                "amount": 10000,
                "currency": "USD",
            }
        ),
    )

    return Consequence(
        consequence_id="consequence-001",
        idempotency_key="payment-release-001",
        action=action,
    )


def test_effect_has_exactly_three_canonical_states() -> None:
    assert set(EffectState) == {
        EffectState.BOUND,
        EffectState.NO_BIND,
        EffectState.EFFECT_UNKNOWN,
    }


@pytest.mark.parametrize(
    ("state", "value"),
    [
        (EffectState.BOUND, "bound"),
        (EffectState.NO_BIND, "no_bind"),
        (EffectState.EFFECT_UNKNOWN, "effect_unknown"),
    ],
)
def test_effect_states_have_stable_values(
    state: EffectState,
    value: str,
) -> None:
    assert state.value == value


def test_decision_states_are_not_effect_states() -> None:
    effect_values = {state.value for state in EffectState}

    assert "admitted" not in effect_values
    assert "held" not in effect_values
    assert "narrowed" not in effect_values
    assert "escalated" not in effect_values
    assert "refused" not in effect_values


def test_effect_references_consequence() -> None:
    consequence = _make_consequence()

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=consequence,
    )

    assert effect.consequence is consequence
    assert effect.state is EffectState.EFFECT_UNKNOWN


def test_effect_unknown_does_not_require_verification() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    assert effect.verification_refs == ()


def test_bound_requires_verification_reference() -> None:
    with pytest.raises(ValueError):
        Effect(
            effect_id="effect-001",
            state=EffectState.BOUND,
            consequence=_make_consequence(),
        )


def test_no_bind_requires_verification_reference() -> None:
    with pytest.raises(ValueError):
        Effect(
            effect_id="effect-001",
            state=EffectState.NO_BIND,
            consequence=_make_consequence(),
        )


def test_bound_can_record_verification_basis() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=_make_consequence(),
        verification_refs=[
            "target-system:transaction-987",
        ],
    )

    assert effect.verification_refs == (
        "target-system:transaction-987",
    )


def test_no_bind_can_record_verification_basis() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.NO_BIND,
        consequence=_make_consequence(),
        verification_refs=[
            "target-system:absence-confirmation-123",
        ],
    )

    assert effect.state is EffectState.NO_BIND


def test_verification_references_cannot_be_blank() -> None:
    with pytest.raises(ValueError):
        Effect(
            effect_id="effect-001",
            state=EffectState.BOUND,
            consequence=_make_consequence(),
            verification_refs=["   "],
        )


def test_effect_requires_valid_state() -> None:
    with pytest.raises(TypeError):
        Effect(
            effect_id="effect-001",
            state="bound",
            consequence=_make_consequence(),
            verification_refs=["target-system:transaction-987"],
        )


def test_effect_is_immutable() -> None:
    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=_make_consequence(),
    )

    with pytest.raises(FrozenInstanceError):
        effect.state = EffectState.BOUND