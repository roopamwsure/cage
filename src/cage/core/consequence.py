from dataclasses import dataclass

from cage.core.action import Action


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class Consequence:
    consequence_id: str
    idempotency_key: str
    action: Action

    def __post_init__(self) -> None:
        _require_non_empty(self.consequence_id, "consequence_id")
        _require_non_empty(self.idempotency_key, "idempotency_key")

        if not isinstance(self.action, Action):
            raise TypeError("action must be an Action")