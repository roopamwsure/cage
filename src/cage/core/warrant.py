from collections.abc import Sequence
from dataclasses import dataclass

from cage.core.decision import Decision
from cage.core.effect import Effect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)

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


@dataclass(frozen=True, slots=True)
class DecisionProof:
    proof_id: str
    decision: Decision
    evidence_refs: Sequence[str] = ()
    standing_refs: Sequence[str] = ()
    delegation_refs: Sequence[str] = ()
    approval_refs: Sequence[str] = ()
    context_refs: Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.proof_id, "proof_id")

        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision")

        for field_name in (
            "evidence_refs",
            "standing_refs",
            "delegation_refs",
            "approval_refs",
            "context_refs",
        ):
            frozen = _freeze_references(
                getattr(self, field_name),
                field_name,
            )
            object.__setattr__(self, field_name, frozen)

def create_decision_proof(
    *,
    proof_id: str,
    decision: Decision,
    evidence: Sequence[Evidence] = (),
    standing: Sequence[Standing] = (),
    delegations: Sequence[Delegation] = (),
    approvals: Sequence[Approval] = (),
    context: Sequence[Context] = (),
) -> DecisionProof:
    return DecisionProof(
        proof_id=proof_id,
        decision=decision,
        evidence_refs=tuple(
            item.evidence_id for item in evidence
        ),
        standing_refs=tuple(
            item.standing_id for item in standing
        ),
        delegation_refs=tuple(
            item.delegation_id for item in delegations
        ),
        approval_refs=tuple(
            item.approval_id for item in approvals
        ),
        context_refs=tuple(
            item.context_id for item in context
        ),
    )            


@dataclass(frozen=True, slots=True)
class EffectProof:
    proof_id: str
    effect: Effect

    def __post_init__(self) -> None:
        _require_non_empty(self.proof_id, "proof_id")

        if not isinstance(self.effect, Effect):
            raise TypeError("effect must be an Effect")

@dataclass(frozen=True, slots=True)
class Warrant:
    warrant_id: str
    schema_version: str
    decision_proof: DecisionProof
    effect_proof: EffectProof | None = None
    previous_warrant_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.warrant_id, "warrant_id")
        _require_non_empty(self.schema_version, "schema_version")

        if not isinstance(self.decision_proof, DecisionProof):
            raise TypeError(
                "decision_proof must be a DecisionProof"
            )

        if (
            self.effect_proof is not None
            and not isinstance(self.effect_proof, EffectProof)
        ):
            raise TypeError(
                "effect_proof must be an EffectProof or None"
            )

        if self.previous_warrant_id is not None:
            _require_non_empty(
                self.previous_warrant_id,
                "previous_warrant_id",
            )

        if self.effect_proof is not None:
            decision_consequence_id = (
                self.decision_proof
                .decision
                .attempt
                .consequence
                .consequence_id
            )

            effect_consequence_id = (
                self.effect_proof
                .effect
                .consequence
                .consequence_id
            )

            if decision_consequence_id != effect_consequence_id:
                raise ValueError(
                    "decision proof and effect proof must refer "
                    "to the same consequence"
                )

    @property
    def consequence_id(self) -> str:
        return (
            self.decision_proof
            .decision
            .attempt
            .consequence
            .consequence_id
        )

    @property
    def action_id(self) -> str:
        return (
            self.decision_proof
            .decision
            .attempt
            .consequence
            .action
            .action_id
        )

    @property
    def attempt_id(self) -> str:
        return (
            self.decision_proof
            .decision
            .attempt
            .attempt_id
        )        