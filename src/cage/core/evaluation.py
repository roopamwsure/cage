from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cage.core.action import RequestedEffect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
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


EvaluationRule = Callable[
    [
        Attempt,
        tuple[Evidence, ...],
        tuple[Standing, ...],
        tuple[Delegation, ...],
        tuple[Approval, ...],
        tuple[Context, ...],
    ],
    EvaluationOutcome,
]


def evaluate_attempt(
    *,
    decision_id: str,
    attempt: Attempt,
    rule: EvaluationRule,
    evidence: Sequence[Evidence] = (),
    standing: Sequence[Standing] = (),
    delegations: Sequence[Delegation] = (),
    approvals: Sequence[Approval] = (),
    context: Sequence[Context] = (),
) -> Decision:
    if not isinstance(decision_id, str):
        raise TypeError("decision_id must be a string")

    if not decision_id.strip():
        raise ValueError("decision_id must not be empty")

    if not isinstance(attempt, Attempt):
        raise TypeError("attempt must be an Attempt")

    if not callable(rule):
        raise TypeError("rule must be callable")

    if isinstance(evidence, str) or not isinstance(evidence, Sequence):
        raise TypeError("evidence must be a sequence of Evidence")

    frozen_evidence = tuple(evidence)

    if not all(isinstance(item, Evidence) for item in frozen_evidence):
        raise TypeError("evidence must contain only Evidence")

    if isinstance(standing, str) or not isinstance(standing, Sequence):
        raise TypeError("standing must be a sequence of Standing")

    frozen_standing = tuple(standing)

    if not all(isinstance(item, Standing) for item in frozen_standing):
        raise TypeError("standing must contain only Standing")

    if (
        isinstance(delegations, str)
        or not isinstance(delegations, Sequence)
    ):
        raise TypeError(
            "delegations must be a sequence of Delegation"
        )

    frozen_delegations = tuple(delegations)

    if not all(
        isinstance(item, Delegation)
        for item in frozen_delegations
    ):
        raise TypeError(
            "delegations must contain only Delegation"
        )

    if isinstance(approvals, str) or not isinstance(approvals, Sequence):
        raise TypeError("approvals must be a sequence of Approval")

    frozen_approvals = tuple(approvals)

    if not all(
        isinstance(item, Approval)
        for item in frozen_approvals
    ):
        raise TypeError(
            "approvals must contain only Approval"
        )

    if isinstance(context, str) or not isinstance(context, Sequence):
        raise TypeError("context must be a sequence of Context")

    frozen_context = tuple(context)

    if not all(isinstance(item, Context) for item in frozen_context):
        raise TypeError("context must contain only Context")

    outcome = rule(
        attempt,
        frozen_evidence,
        frozen_standing,
        frozen_delegations,
        frozen_approvals,
        frozen_context,
    )

    if not isinstance(outcome, EvaluationOutcome):
        raise TypeError("rule must return an EvaluationOutcome")

    return Decision(
        decision_id=decision_id,
        state=outcome.state,
        attempt=attempt,
        permitted_effect=outcome.permitted_effect,
    )