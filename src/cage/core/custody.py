from cage.core.action import RequestedEffect
from cage.core.decision import Decision, DecisionState


class CustodyIneligibleError(ValueError):
    """Raised when a Decision is not eligible for execution custody."""


def select_effect_for_custody(
    decision: Decision,
) -> RequestedEffect:
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")

    if decision.state is DecisionState.ADMITTED:
        return (
            decision
            .attempt
            .consequence
            .action
            .requested_effect
        )

    if decision.state is DecisionState.NARROWED:
        if decision.permitted_effect is None:
            raise ValueError(
                "NARROWED decision requires a permitted_effect"
            )

        return decision.permitted_effect

    raise CustodyIneligibleError(
        f"{decision.state.value} decision is not eligible for custody"
    )