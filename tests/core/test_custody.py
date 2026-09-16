import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.custody import (
    CustodyIneligibleError,
    select_effect_for_custody,
)
from cage.core.decision import Decision, DecisionState
from cage.core.identity import Agent, Principal, Resource


def _make_attempt() -> Attempt:
    action = Action(
        action_id="action-001",
        action_type="access.grant",
        principal=Principal(
            principal_id="principal-123",
        ),
        agent=Agent(
            agent_id="agent-456",
        ),
        resource=Resource(
            resource_id="account-789",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "role": "global-admin",
                "duration_minutes": 480,
            }
        ),
    )

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="access-grant-global-admin",
        action=action,
    )

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def test_admitted_decision_selects_original_requested_effect() -> None:
    attempt = _make_attempt()

    decision = Decision(
        decision_id="decision-admitted-001",
        state=DecisionState.ADMITTED,
        attempt=attempt,
    )

    selected = select_effect_for_custody(decision)

    assert (
        selected
        is attempt.consequence.action.requested_effect
    )


def test_narrowed_decision_selects_only_permitted_effect() -> None:
    attempt = _make_attempt()

    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted_effect,
    )

    selected = select_effect_for_custody(decision)

    assert selected is permitted_effect

    assert (
        selected
        is not attempt.consequence.action.requested_effect
    )

    assert selected.parameters["role"] == "scoped-operator"
    assert selected.parameters["duration_minutes"] == 30


@pytest.mark.parametrize(
    "state",
    [
        DecisionState.HELD,
        DecisionState.ESCALATED,
        DecisionState.REFUSED,
    ],
)
def test_ineligible_decisions_cannot_enter_custody(
    state: DecisionState,
) -> None:
    decision = Decision(
        decision_id=f"decision-{state.value}-001",
        state=state,
        attempt=_make_attempt(),
    )

    with pytest.raises(
        CustodyIneligibleError,
        match=f"{state.value} decision is not eligible for custody",
    ):
        select_effect_for_custody(decision)


def test_select_effect_for_custody_requires_decision() -> None:
    with pytest.raises(
        TypeError,
        match="decision must be a Decision",
    ):
        select_effect_for_custody(
            "decision-001",  # type: ignore[arg-type]
        )


def test_narrowed_original_effect_remains_preserved() -> None:
    attempt = _make_attempt()

    original_effect = attempt.consequence.action.requested_effect

    permitted_effect = RequestedEffect(
        parameters={
            "role": "scoped-operator",
            "duration_minutes": 30,
        }
    )

    decision = Decision(
        decision_id="decision-narrowed-001",
        state=DecisionState.NARROWED,
        attempt=attempt,
        permitted_effect=permitted_effect,
    )

    selected = select_effect_for_custody(decision)

    assert selected is permitted_effect

    assert (
        original_effect.parameters["role"]
        == "global-admin"
    )
    assert (
        original_effect.parameters["duration_minutes"]
        == 480
    )