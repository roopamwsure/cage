from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from cage.core.execution import ExecutionAttempt


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _freeze_references(
    references: Sequence[str],
    field_name: str,
) -> tuple[str, ...]:
    if isinstance(references, str):
        raise TypeError(f"{field_name} must be a sequence of strings")

    if not isinstance(references, Sequence):
        raise TypeError(f"{field_name} must be a sequence of strings")

    frozen = tuple(references)

    for reference in frozen:
        _require_non_empty(reference, field_name)

    return frozen


class AdapterExecutionState(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AdapterExecutionResult:
    result_id: str
    execution_attempt: ExecutionAttempt
    state: AdapterExecutionState
    references: Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.result_id, "result_id")

        if not isinstance(
            self.execution_attempt,
            ExecutionAttempt,
        ):
            raise TypeError(
                "execution_attempt must be an ExecutionAttempt"
            )

        if not isinstance(self.state, AdapterExecutionState):
            raise TypeError(
                "state must be an AdapterExecutionState"
            )

        frozen_references = _freeze_references(
            self.references,
            "references",
        )

        object.__setattr__(
            self,
            "references",
            frozen_references,
        )