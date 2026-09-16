import pytest

from cage.core.capability import ExecutionCapability


def test_execution_capability_records_structural_binding() -> None:
    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-001",
        action_type="database.delete",
        resource_id="database-789",
    )

    assert capability.capability_id == "capability-001"
    assert capability.consequence_id == "consequence-001"
    assert capability.action_type == "database.delete"
    assert capability.resource_id == "database-789"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("capability_id", ""),
        ("capability_id", "   "),
        ("consequence_id", ""),
        ("consequence_id", "   "),
        ("action_type", ""),
        ("action_type", "   "),
        ("resource_id", ""),
        ("resource_id", "   "),
    ],
)
def test_execution_capability_requires_non_empty_fields(
    field_name: str,
    value: str,
) -> None:
    values = {
        "capability_id": "capability-001",
        "consequence_id": "consequence-001",
        "action_type": "database.delete",
        "resource_id": "database-789",
    }

    values[field_name] = value

    with pytest.raises(ValueError):
        ExecutionCapability(**values)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("capability_id", 123),
        ("consequence_id", 123),
        ("action_type", 123),
        ("resource_id", 123),
    ],
)
def test_execution_capability_requires_string_fields(
    field_name: str,
    value: object,
) -> None:
    values = {
        "capability_id": "capability-001",
        "consequence_id": "consequence-001",
        "action_type": "database.delete",
        "resource_id": "database-789",
    }

    values[field_name] = value

    with pytest.raises(TypeError):
        ExecutionCapability(**values)  # type: ignore[arg-type]


def test_execution_capability_is_immutable() -> None:
    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-001",
        action_type="database.delete",
        resource_id="database-789",
    )

    with pytest.raises(AttributeError):
        capability.resource_id = "database-999"


def test_execution_capability_contains_no_provider_credentials() -> None:
    capability = ExecutionCapability(
        capability_id="capability-001",
        consequence_id="consequence-001",
        action_type="database.delete",
        resource_id="database-789",
    )

    assert not hasattr(capability, "token")
    assert not hasattr(capability, "secret")
    assert not hasattr(capability, "credential")
    assert not hasattr(capability, "provider")
    assert not hasattr(capability, "policy")