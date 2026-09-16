import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.idempotency import (
    IdempotencyConflictError,
    IdempotencyRegistry,
)
from cage.core.identity import Agent, Principal, Resource
from cage.core.replay import create_replay_attempt


def _make_consequence(
    *,
    consequence_id: str = "consequence-001",
    action_id: str = "action-001",
    database: str = "customers",
    idempotency_key: str = "delete-prod-customers-001",
    action_type: str = "database.delete",
    principal_id: str = "principal-123",
    agent_id: str = "agent-456",
    resource_id: str = "database-service",
    parameters: dict[str, object] | None = None,
) -> Consequence:
    if parameters is None:
        parameters = {
            "database": database,
            "environment": "production",
        }

    action = Action(
        action_id=action_id,
        action_type=action_type,
        principal=Principal(principal_id=principal_id),
        agent=Agent(agent_id=agent_id),
        resource=Resource(resource_id=resource_id),
        requested_effect=RequestedEffect(
            parameters=parameters,
        ),
    )

    return Consequence(
        consequence_id=consequence_id,
        idempotency_key=idempotency_key,
        action=action,
    )


def test_first_consequence_is_registered() -> None:
    registry = IdempotencyRegistry()
    consequence = _make_consequence()

    resolved = registry.resolve(consequence)

    assert resolved is consequence


def test_same_key_and_same_intent_return_original_consequence() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        consequence_id="consequence-001",
        action_id="action-001",
    )

    retry = _make_consequence(
        consequence_id="consequence-999",
        action_id="action-999",
    )

    original = registry.resolve(first)
    resolved_retry = registry.resolve(retry)

    assert resolved_retry is original
    assert resolved_retry.consequence_id == "consequence-001"


def test_same_key_and_different_intent_raise_conflict() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        database="customers",
    )

    conflicting = _make_consequence(
        consequence_id="consequence-002",
        action_id="action-002",
        database="payroll",
    )

    registry.resolve(first)

    with pytest.raises(IdempotencyConflictError):
        registry.resolve(conflicting)


def test_different_keys_can_represent_different_consequences() -> None:
    registry = IdempotencyRegistry()

    customers = _make_consequence(
        consequence_id="consequence-customers",
        database="customers",
        idempotency_key="delete-customers-001",
    )

    payroll = _make_consequence(
        consequence_id="consequence-payroll",
        database="payroll",
        idempotency_key="delete-payroll-001",
    )

    resolved_customers = registry.resolve(customers)
    resolved_payroll = registry.resolve(payroll)

    assert resolved_customers is customers
    assert resolved_payroll is payroll
    assert (
        resolved_customers.consequence_id
        != resolved_payroll.consequence_id
    )


def test_registry_requires_consequence() -> None:
    registry = IdempotencyRegistry()

    with pytest.raises(TypeError):
        registry.resolve("not-a-consequence")


def test_parameter_order_does_not_change_consequence_semantics() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        consequence_id="consequence-001",
        parameters={
            "database": "customers",
            "environment": "production",
            "options": {
                "backup": True,
                "cascade": False,
            },
        },
    )

    retry = _make_consequence(
        consequence_id="consequence-999",
        action_id="action-999",
        parameters={
            "options": {
                "cascade": False,
                "backup": True,
            },
            "environment": "production",
            "database": "customers",
        },
    )

    original = registry.resolve(first)
    resolved = registry.resolve(retry)

    assert resolved is original


def test_same_key_with_different_action_type_conflicts() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        action_type="database.delete",
    )

    conflicting = _make_consequence(
        consequence_id="consequence-002",
        action_id="action-002",
        action_type="database.backup",
    )

    registry.resolve(first)

    with pytest.raises(IdempotencyConflictError):
        registry.resolve(conflicting)


def test_same_key_with_different_resource_conflicts() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        resource_id="database-service-prod",
    )

    conflicting = _make_consequence(
        consequence_id="consequence-002",
        action_id="action-002",
        resource_id="database-service-dev",
    )

    registry.resolve(first)

    with pytest.raises(IdempotencyConflictError):
        registry.resolve(conflicting)


def test_same_key_with_different_principal_conflicts() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        principal_id="principal-123",
    )

    conflicting = _make_consequence(
        consequence_id="consequence-002",
        action_id="action-002",
        principal_id="principal-999",
    )

    registry.resolve(first)

    with pytest.raises(IdempotencyConflictError):
        registry.resolve(conflicting)


def test_retry_can_create_new_attempt_without_new_consequence() -> None:
    registry = IdempotencyRegistry()

    first_request = _make_consequence(
        consequence_id="consequence-001",
        action_id="action-001",
    )

    retry_request = _make_consequence(
        consequence_id="consequence-999",
        action_id="action-999",
    )

    original = registry.resolve(first_request)
    resolved_retry = registry.resolve(retry_request)

    first_attempt = Attempt(
        attempt_id="attempt-001",
        consequence=original,
    )

    retry_attempt = create_replay_attempt(
        previous_attempt=first_attempt,
        attempt_id="attempt-002",
    )

    assert resolved_retry is original

    assert (
        retry_attempt.consequence
        is original
    )

    assert (
        retry_attempt.consequence.consequence_id
        == "consequence-001"
    )

    assert retry_attempt.attempt_id == "attempt-002"


def test_same_key_and_intent_can_resolve_across_agents() -> None:
    registry = IdempotencyRegistry()

    first = _make_consequence(
        consequence_id="consequence-001",
        action_id="action-001",
        agent_id="agent-111",
    )

    retry = _make_consequence(
        consequence_id="consequence-999",
        action_id="action-999",
        agent_id="agent-222",
    )

    original = registry.resolve(first)
    resolved = registry.resolve(retry)

    assert resolved is original
    assert resolved.consequence_id == "consequence-001"
