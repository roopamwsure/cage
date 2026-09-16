from dataclasses import dataclass

from cage.core.consequence import Consequence
from cage.core.decision import Decision


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class ExecutionAttempt:
    execution_attempt_id: str
    decision: Decision
    previous_execution_attempt_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(
            self.execution_attempt_id,
            "execution_attempt_id",
        )

        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision")

        if self.previous_execution_attempt_id is not None:
            _require_non_empty(
                self.previous_execution_attempt_id,
                "previous_execution_attempt_id",
            )

            if (
                self.previous_execution_attempt_id
                == self.execution_attempt_id
            ):
                raise ValueError(
                    "previous_execution_attempt_id must differ "
                    "from execution_attempt_id"
                )

    @property
    def consequence(self) -> Consequence:
        return self.decision.attempt.consequence