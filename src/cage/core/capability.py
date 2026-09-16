from dataclasses import dataclass


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class ExecutionCapability:
    capability_id: str
    consequence_id: str
    action_type: str
    resource_id: str

    def __post_init__(self) -> None:
        _require_non_empty(
            self.capability_id,
            "capability_id",
        )
        _require_non_empty(
            self.consequence_id,
            "consequence_id",
        )
        _require_non_empty(
            self.action_type,
            "action_type",
        )
        _require_non_empty(
            self.resource_id,
            "resource_id",
        )