from dataclasses import FrozenInstanceError

import pytest

from cage.core.identity import Agent, Principal, Resource


def test_identity_contracts_accept_generic_identifiers() -> None:
    principal = Principal(principal_id="principal-123")
    agent = Agent(agent_id="agent-456")
    resource = Resource(resource_id="resource-789")

    assert principal.principal_id == "principal-123"
    assert agent.agent_id == "agent-456"
    assert resource.resource_id == "resource-789"


@pytest.mark.parametrize(
    ("identity_type", "field_name"),
    [
        (Principal, "principal_id"),
        (Agent, "agent_id"),
        (Resource, "resource_id"),
    ],
)
def test_identity_identifiers_cannot_be_blank(identity_type, field_name) -> None:
    with pytest.raises(ValueError):
        identity_type(**{field_name: "   "})


def test_identity_contracts_are_immutable() -> None:
    principal = Principal(principal_id="principal-123")

    with pytest.raises(FrozenInstanceError):
        principal.principal_id = "changed"
