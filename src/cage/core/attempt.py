from dataclasses import dataclass

from cage.core.consequence import Consequence


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: str
    consequence: Consequence
    previous_attempt_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.attempt_id, "attempt_id")

        if not isinstance(self.consequence, Consequence):
            raise TypeError("consequence must be a Consequence")

        if self.previous_attempt_id is not None:
            _require_non_empty(
                self.previous_attempt_id,
                "previous_attempt_id",
            )