from dataclasses import dataclass


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str

    def __post_init__(self) -> None:
        _require_non_empty(self.principal_id, "principal_id")


@dataclass(frozen=True, slots=True)
class Agent:
    agent_id: str

    def __post_init__(self) -> None:
        _require_non_empty(self.agent_id, "agent_id")


@dataclass(frozen=True, slots=True)
class Resource:
    resource_id: str

    def __post_init__(self) -> None:
        _require_non_empty(self.resource_id, "resource_id")
