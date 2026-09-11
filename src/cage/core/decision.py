from dataclasses import dataclass
from enum import StrEnum

from cage.core.action import RequestedEffect
from cage.core.attempt import Attempt


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


class DecisionState(StrEnum):
    ADMITTED = "admitted"
    HELD = "held"
    NARROWED = "narrowed"
    ESCALATED = "escalated"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class Decision:
    decision_id: str
    state: DecisionState
    attempt: Attempt
    permitted_effect: RequestedEffect | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.decision_id, "decision_id")

        if not isinstance(self.state, DecisionState):
            raise TypeError("state must be a DecisionState")

        if not isinstance(self.attempt, Attempt):
            raise TypeError("attempt must be an Attempt")

        if (
            self.permitted_effect is not None
            and not isinstance(self.permitted_effect, RequestedEffect)
        ):
            raise TypeError(
                "permitted_effect must be a RequestedEffect or None"
            )

        if (
            self.state is DecisionState.NARROWED
            and self.permitted_effect is None
        ):
            raise ValueError(
                "NARROWED decisions require a permitted_effect"
            )

        if (
            self.state is not DecisionState.NARROWED
            and self.permitted_effect is not None
        ):
            raise ValueError(
                "permitted_effect is only valid for NARROWED decisions"
            )