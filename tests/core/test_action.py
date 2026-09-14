import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.identity import Agent, Principal, Resource


def test_requested_effect_accepts_different_domains() -> None:
    payment = RequestedEffect(
        parameters={
            "amount": 5000,
            "currency": "USD",
        }
    )
    access = RequestedEffect(
        parameters={
            "role": "admin",
            "duration_minutes": 30,
        }
    )
    database = RequestedEffect(
        parameters={
            "database": "customers",
            "environment": "production",
        }
    )

    assert payment.parameters["currency"] == "USD"
    assert access.parameters["duration_minutes"] == 30
    assert database.parameters["environment"] == "production"


def test_requested_effect_accepts_empty_parameters() -> None:
    effect = RequestedEffect(parameters={})

    assert dict(effect.parameters) == {}


def test_requested_effect_cannot_be_modified() -> None:
    effect = RequestedEffect(
        parameters={
            "environment": "production",
        }
    )

    with pytest.raises(TypeError):
        effect.parameters["environment"] = "development"


def test_requested_effect_isolated_from_original_input() -> None:
    parameters = {
        "environment": "production",
    }

    effect = RequestedEffect(parameters=parameters)

    parameters["environment"] = "development"

    assert effect.parameters["environment"] == "production"


def test_requested_effect_rejects_non_mapping_parameters() -> None:
    with pytest.raises(
        TypeError,
        match="parameters must be a mapping",
    ):
        RequestedEffect(
            parameters=["production"]  # type: ignore[arg-type]
        )


def test_requested_effect_rejects_non_json_values() -> None:
    with pytest.raises(TypeError):
        RequestedEffect(
            parameters={
                "invalid": object(),
            }
        )


def test_requested_effect_rejects_non_string_keys() -> None:
    with pytest.raises(TypeError):
        RequestedEffect(
            parameters={
                123: "invalid",
            }
        )


def test_requested_effect_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        RequestedEffect(
            parameters={
                "amount": float("nan"),
            }
        )


def test_action_represents_generic_proposal() -> None:
    action = Action(
        action_id="action-001",
        action_type="database.delete",
        principal=Principal(
            principal_id="user-123",
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

    assert action.action_id == "action-001"
    assert action.action_type == "database.delete"
    assert action.principal.principal_id == "user-123"
    assert action.agent.agent_id == "agent-456"
    assert action.resource.resource_id == "database-789"
    assert (
        action.requested_effect.parameters["environment"]
        == "production"
    )


def test_same_action_contract_supports_different_domains() -> None:
    principal = Principal(
        principal_id="principal-123",
    )
    agent = Agent(
        agent_id="agent-456",
    )

    database_action = Action(
        action_id="action-db",
        action_type="database.delete",
        principal=principal,
        agent=agent,
        resource=Resource(
            resource_id="database-1",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "environment": "production",
            }
        ),
    )

    access_action = Action(
        action_id="action-access",
        action_type="access.grant",
        principal=principal,
        agent=agent,
        resource=Resource(
            resource_id="account-1",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "role": "operator",
                "duration_minutes": 30,
            }
        ),
    )

    payment_action = Action(
        action_id="action-payment",
        action_type="payment.release",
        principal=principal,
        agent=agent,
        resource=Resource(
            resource_id="payment-system-1",
        ),
        requested_effect=RequestedEffect(
            parameters={
                "amount": 5000,
                "currency": "USD",
            }
        ),
    )

    assert database_action.action_type == "database.delete"
    assert access_action.action_type == "access.grant"
    assert payment_action.action_type == "payment.release"

    assert (
        database_action.requested_effect.parameters["environment"]
        == "production"
    )
    assert (
        access_action.requested_effect.parameters["role"]
        == "operator"
    )
    assert (
        payment_action.requested_effect.parameters["currency"]
        == "USD"
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("action_id", ""),
        ("action_id", "   "),
        ("action_type", ""),
        ("action_type", "   "),
    ],
)
def test_action_requires_non_empty_identifiers(
    field_name: str,
    value: str,
) -> None:
    values = {
        "action_id": "action-001",
        "action_type": "database.delete",
        "principal": Principal(
            principal_id="principal-123",
        ),
        "agent": Agent(
            agent_id="agent-456",
        ),
        "resource": Resource(
            resource_id="database-789",
        ),
        "requested_effect": RequestedEffect(
            parameters={},
        ),
    }

    values[field_name] = value

    with pytest.raises(ValueError):
        Action(**values)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        (
            "principal",
            "principal-123",
            "principal must be a Principal",
        ),
        (
            "agent",
            "agent-456",
            "agent must be an Agent",
        ),
        (
            "resource",
            "database-789",
            "resource must be a Resource",
        ),
        (
            "requested_effect",
            {},
            "requested_effect must be a RequestedEffect",
        ),
    ],
)
def test_action_rejects_invalid_component_types(
    field_name: str,
    value: object,
    message: str,
) -> None:
    values = {
        "action_id": "action-001",
        "action_type": "database.delete",
        "principal": Principal(
            principal_id="principal-123",
        ),
        "agent": Agent(
            agent_id="agent-456",
        ),
        "resource": Resource(
            resource_id="database-789",
        ),
        "requested_effect": RequestedEffect(
            parameters={},
        ),
    }

    values[field_name] = value

    with pytest.raises(
        TypeError,
        match=message,
    ):
        Action(**values)