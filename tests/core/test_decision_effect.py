from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.effect import Effect, EffectState
from cage.core.identity import Agent, Principal, Resource


def _make_attempt() -> Attempt:
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

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="payment-release-001",
        action=action,
    )

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def test_admitted_decision_can_have_unknown_effect() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=attempt.consequence,
    )

    assert decision.state is DecisionState.ADMITTED
    assert effect.state is EffectState.EFFECT_UNKNOWN


def test_admitted_decision_can_result_in_no_bind() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.NO_BIND,
        consequence=attempt.consequence,
        verification_refs=[
            "target-system:no-effect-confirmation-123",
        ],
    )

    assert decision.state is DecisionState.ADMITTED
    assert effect.state is EffectState.NO_BIND


def test_admitted_decision_can_result_in_bound_effect() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.BOUND,
        consequence=attempt.consequence,
        verification_refs=[
            "target-system:transaction-987",
        ],
    )

    assert decision.state is DecisionState.ADMITTED
    assert effect.state is EffectState.BOUND


def test_refused_decision_does_not_imply_no_bind() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.REFUSED,
        attempt=attempt,
    )

    effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=attempt.consequence,
    )

    assert decision.state is DecisionState.REFUSED
    assert effect.state is EffectState.EFFECT_UNKNOWN


def test_effect_state_can_change_as_external_reality_is_verified() -> None:
    attempt = _make_attempt()

    unknown_effect = Effect(
        effect_id="effect-001",
        state=EffectState.EFFECT_UNKNOWN,
        consequence=attempt.consequence,
    )

    verified_effect = Effect(
        effect_id="effect-002",
        state=EffectState.BOUND,
        consequence=attempt.consequence,
        verification_refs=[
            "target-system:transaction-987",
        ],
    )

    assert (
        unknown_effect.consequence.consequence_id
        == verified_effect.consequence.consequence_id
    )
    assert unknown_effect.state is EffectState.EFFECT_UNKNOWN
    assert verified_effect.state is EffectState.BOUND