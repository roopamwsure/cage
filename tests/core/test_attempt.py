from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.identity import Agent, Principal, Resource


def _make_consequence() -> Consequence:
    action = Action(
        action_id="action-001",
        action_type="database.delete",
        principal=Principal(principal_id="principal-123"),
        agent=Agent(agent_id="agent-456"),
        resource=Resource(resource_id="database-789"),
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


def test_attempt_references_a_consequence() -> None:
    consequence = _make_consequence()

    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    assert attempt.attempt_id == "attempt-001"
    assert attempt.consequence.consequence_id == "consequence-001"


def test_multiple_attempts_can_reference_same_consequence() -> None:
    consequence = _make_consequence()

    first = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    second = Attempt(
        attempt_id="attempt-002",
        consequence=consequence,
        previous_attempt_id=first.attempt_id,
    )

    assert first.attempt_id != second.attempt_id
    assert (
        first.consequence.consequence_id
        == second.consequence.consequence_id
    )
    assert second.previous_attempt_id == "attempt-001"


def test_attempt_requires_non_empty_attempt_id() -> None:
    with pytest.raises(ValueError):
        Attempt(
            attempt_id="   ",
            consequence=_make_consequence(),
        )


def test_previous_attempt_id_cannot_be_blank() -> None:
    with pytest.raises(ValueError):
        Attempt(
            attempt_id="attempt-002",
            consequence=_make_consequence(),
            previous_attempt_id="",
        )


def test_attempt_is_immutable() -> None:
    attempt = Attempt(
        attempt_id="attempt-001",
        consequence=_make_consequence(),
    )

    with pytest.raises(FrozenInstanceError):
        attempt.attempt_id = "changed"

def test_new_attempt_does_not_create_new_consequence() -> None:
    consequence = _make_consequence()

    first = Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )

    second = Attempt(
        attempt_id="attempt-002",
        consequence=consequence,
        previous_attempt_id=first.attempt_id,
    )

    assert first.consequence is consequence
    assert second.consequence is consequence
    assert first.consequence is second.consequence        