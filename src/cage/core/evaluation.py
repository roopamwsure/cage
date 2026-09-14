from collections.abc import Callable
from dataclasses import dataclass

from cage.core.action import RequestedEffect
from cage.core.attempt import Attempt
from cage.core.decision import Decision, DecisionState


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    state: DecisionState
    permitted_effect: RequestedEffect | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, DecisionState):
            raise TypeError("state must be a DecisionState")

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
                "NARROWED outcomes require a permitted_effect"
            )

        if (
            self.state is not DecisionState.NARROWED
            and self.permitted_effect is not None
        ):
            raise ValueError(
                "permitted_effect is only valid for NARROWED outcomes"
            )


EvaluationRule = Callable[[Attempt], EvaluationOutcome]


def evaluate_attempt(
    *,
    decision_id: str,
    attempt: Attempt,
    rule: EvaluationRule,
) -> Decision:
    if not isinstance(decision_id, str):
        raise TypeError("decision_id must be a string")

    if not decision_id.strip():
        raise ValueError("decision_id must not be empty")

    if not isinstance(attempt, Attempt):
        raise TypeError("attempt must be an Attempt")

    if not callable(rule):
        raise TypeError("rule must be callable")

    outcome = rule(attempt)

    if not isinstance(outcome, EvaluationOutcome):
        raise TypeError("rule must return an EvaluationOutcome")

    return Decision(
        decision_id=decision_id,
        state=outcome.state,
        attempt=attempt,
        permitted_effect=outcome.permitted_effect,
    )