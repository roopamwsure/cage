from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision, DecisionState
from cage.core.identity import Agent, Principal, Resource


def _make_attempt() -> Attempt:
    action = Action(
        action_id="action-001",
        action_type="access.grant",
        principal=Principal(principal_id="principal-123"),
        agent=Agent(agent_id="agent-456"),
        resource=Resource(resource_id="account-789"),
        requested_effect=RequestedEffect(
            parameters={
                "role": "global_admin",
                "duration": "unlimited",
            }
        ),
    )

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="grant-access-001",
        action=action,
    )

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def test_decision_has_exactly_five_canonical_states() -> None:
    assert set(DecisionState) == {
        DecisionState.ADMITTED,
        DecisionState.HELD,
        DecisionState.NARROWED,
        DecisionState.ESCALATED,
        DecisionState.REFUSED,
    }


@pytest.mark.parametrize(
    ("state", "value"),
    [
        (DecisionState.ADMITTED, "admitted"),
        (DecisionState.HELD, "held"),
        (DecisionState.NARROWED, "narrowed"),
        (DecisionState.ESCALATED, "escalated"),
        (DecisionState.REFUSED, "refused"),
    ],
)
def test_decision_states_have_stable_values(
    state: DecisionState,
    value: str,
) -> None:
    assert state.value == value


def test_no_bind_is_not_a_decision_state() -> None:
    assert "no_bind" not in {state.value for state in DecisionState}


def test_effect_unknown_is_not_a_decision_state() -> None:
    assert "effect_unknown" not in {
        state.value for state in DecisionState
    }


def test_decision_references_evaluation_attempt() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    assert decision.state is DecisionState.ADMITTED
    assert decision.attempt.attempt_id == "attempt-001"
    assert (
        decision.attempt.consequence.consequence_id
        == "consequence-001"
    )


def test_narrowed_decision_requires_permitted_effect() -> None:
    with pytest.raises(ValueError):
        Decision(
            decision_id="decision-001",
            state=DecisionState.NARROWED,
            attempt=_make_attempt(),
        )


def test_narrowed_decision_preserves_requested_and_permitted_effects() -> None:
    attempt = _make_attempt()

    permitted = RequestedEffect(
        parameters={
            "role": "scoped_operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted,
    )

    requested = (
        decision.attempt
        .consequence
        .action
        .requested_effect
    )

    assert requested.parameters["role"] == "global_admin"
    assert decision.permitted_effect is permitted
    assert (
        decision.permitted_effect.parameters["role"]
        == "scoped_operator"
    )
    assert (
        decision.permitted_effect.parameters["duration_minutes"]
        == 30
    )


def test_non_narrowed_decision_rejects_permitted_effect() -> None:
    permitted = RequestedEffect(
        parameters={
            "role": "scoped_operator",
            "duration_minutes": 30,
        }
    )

    with pytest.raises(ValueError):
        Decision(
            decision_id="decision-001",
            state=DecisionState.ADMITTED,
            attempt=_make_attempt(),
            permitted_effect=permitted,
        )


def test_decision_requires_valid_state() -> None:
    with pytest.raises(TypeError):
        Decision(
            decision_id="decision-001",
            state="admitted",
            attempt=_make_attempt(),
        )


def test_decision_requires_non_empty_decision_id() -> None:
    with pytest.raises(ValueError):
        Decision(
            decision_id="   ",
            state=DecisionState.HELD,
            attempt=_make_attempt(),
        )


def test_decision_requires_attempt() -> None:
    with pytest.raises(TypeError):
        Decision(
            decision_id="decision-001",
            state=DecisionState.HELD,
            attempt="attempt-001",
        )


def test_decision_is_immutable() -> None:
    decision = Decision(
        decision_id="decision-001",
        state=DecisionState.HELD,
        attempt=_make_attempt(),
    )

    with pytest.raises(FrozenInstanceError):
        decision.state = DecisionState.ADMITTED