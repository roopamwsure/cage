from dataclasses import FrozenInstanceError

import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.consequence import Consequence
from cage.core.identity import Agent, Principal, Resource


def _make_action() -> Action:
    return Action(
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


def test_consequence_wraps_an_intended_action() -> None:
    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="delete-customers-production",
        action=_make_action(),
    )

    assert consequence.consequence_id == "consequence-001"
    assert consequence.action.action_type == "database.delete"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("consequence_id", ""),
        ("idempotency_key", "   "),
    ],
)
def test_consequence_requires_non_empty_identifiers(
    field_name: str,
    value: str,
) -> None:
    values = {
        "consequence_id": "consequence-001",
        "idempotency_key": "delete-customers-production",
        "action": _make_action(),
    }

    values[field_name] = value

    with pytest.raises(ValueError):
        Consequence(**values)


def test_consequence_is_immutable() -> None:
    consequence = Consequence(
        consequence_id="consequence-001",
        idempotency_key="delete-customers-production",
        action=_make_action(),
    )

    with pytest.raises(FrozenInstanceError):
        consequence.consequence_id = "changed"