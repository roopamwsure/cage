from inspect import signature
import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.identity import Agent, Principal, Resource
from cage.core.replay import create_replay_attempt


def _make_attempt() -> Attempt:
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

    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="delete-customers-production",
        action=action,
    )

    return Attempt(
        attempt_id="attempt-001",
        consequence=consequence,
    )


def test_replay_creates_new_attempt_for_same_consequence() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert replay.attempt_id == "attempt-002"
    assert replay.consequence is first.consequence
    assert (
        replay.consequence.consequence_id
        == first.consequence.consequence_id
    )


def test_replay_links_to_previous_attempt() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert replay.previous_attempt_id == "attempt-001"


def test_replay_requires_new_attempt_identity() -> None:
    first = _make_attempt()

    with pytest.raises(ValueError):
        create_replay_attempt(
            previous_attempt=first,
            attempt_id="attempt-001",
        )


def test_replay_can_be_chained() -> None:
    first = _make_attempt()

    second = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    third = create_replay_attempt(
        previous_attempt=second,
        attempt_id="attempt-003",
    )

    assert second.previous_attempt_id == "attempt-001"
    assert third.previous_attempt_id == "attempt-002"

    assert first.consequence is second.consequence
    assert second.consequence is third.consequence


def test_replay_does_not_modify_previous_attempt() -> None:
    first = _make_attempt()

    create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert first.attempt_id == "attempt-001"
    assert first.previous_attempt_id is None

def test_replay_preserves_original_action() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert replay.consequence.action is first.consequence.action
    assert (
        replay.consequence.action.action_id
        == first.consequence.action.action_id
    )


def test_replay_preserves_original_requested_effect() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    original_effect = (
        first.consequence.action.requested_effect
    )
    replay_effect = (
        replay.consequence.action.requested_effect
    )

    assert replay_effect is original_effect
    assert (
        replay_effect.parameters["database"]
        == "customers"
    )
    assert (
        replay_effect.parameters["environment"]
        == "production"
    )


def test_replay_preserves_idempotency_key() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert (
        replay.consequence.idempotency_key
        == first.consequence.idempotency_key
    )


def test_replay_does_not_create_new_consequence_identity() -> None:
    first = _make_attempt()

    replay = create_replay_attempt(
        previous_attempt=first,
        attempt_id="attempt-002",
    )

    assert (
        replay.consequence.consequence_id
        == "consequence-001"
    )
    assert replay.consequence is first.consequence 

def test_replay_primitive_has_no_execution_dependency() -> None:
    parameters = signature(create_replay_attempt).parameters

    assert tuple(parameters) == (
        "previous_attempt",
        "attempt_id",
    )       