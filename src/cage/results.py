from dataclasses import dataclass

from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.decision import Decision
from cage.core.warrant import DecisionProof, Warrant
from cage.errors import CAGETypeError, CAGEValueError


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Immutable developer view of a completed evaluation."""

    warrant: Warrant

    def __post_init__(self) -> None:
        if not isinstance(self.warrant, Warrant):
            raise CAGETypeError("warrant must be a Warrant")

        if self.warrant.effect_proof is not None:
            raise CAGEValueError(
                "EvaluationResult requires a decision-only Warrant"
            )

    @property
    def decision_proof(self) -> DecisionProof:
        return self.warrant.decision_proof

    @property
    def decision(self) -> Decision:
        return self.decision_proof.decision

    @property
    def attempt(self) -> Attempt:
        return self.decision.attempt

    @property
    def consequence(self) -> Consequence:
        return self.attempt.consequence

    @property
    def consequence_id(self) -> str:
        return self.consequence.consequence_id

    @property
    def idempotency_key(self) -> str:
        return self.consequence.idempotency_key