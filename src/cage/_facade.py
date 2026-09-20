from collections.abc import Sequence

from cage.config import CAGEConfig
from cage.core.action import Action
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.attempt import Attempt
from cage.core.consequence import Consequence
from cage.core.evaluation import (
    EvaluationRule,
    evaluate_attempt,
)
from cage.core.idempotency import IdempotencyRegistry
from cage.core.warrant import Warrant, create_decision_proof
from cage.errors import CAGETypeError
from cage.identifiers import (
    EvaluationIds,
    IdentityKind,
    _generate_id,
)
from cage.inputs import CAGEInputs
from cage.results import EvaluationResult


class CAGE:
    """High-level orchestrator for the CAGE lifecycle."""

    __slots__ = (
        "_config",
        "_idempotency_registry",
        "_inputs",
        "_rule",
    )

    def __init__(
        self,
        *,
        rule: EvaluationRule,
        config: CAGEConfig | None = None,
    ) -> None:
        if not callable(rule):
            raise CAGETypeError("rule must be callable")

        if config is not None and not isinstance(config, CAGEConfig):
            raise CAGETypeError(
                "config must be a CAGEConfig or None"
            )

        resolved_config = CAGEConfig() if config is None else config

        self._rule = rule
        self._config = resolved_config
        self._inputs = CAGEInputs(
            id_factory=resolved_config.id_factory
        )
        self._idempotency_registry = IdempotencyRegistry()

    @property
    def config(self) -> CAGEConfig:
        return self._config

    @property
    def inputs(self) -> CAGEInputs:
        return self._inputs

    def evaluate(
        self,
        *,
        action: Action,
        idempotency_key: str,
        evidence: Sequence[Evidence] = (),
        standing: Sequence[Standing] = (),
        delegations: Sequence[Delegation] = (),
        approvals: Sequence[Approval] = (),
        context: Sequence[Context] = (),
        ids: EvaluationIds | None = None,
    ) -> EvaluationResult:
        if ids is not None and not isinstance(ids, EvaluationIds):
            raise CAGETypeError(
                "ids must be an EvaluationIds or None"
            )

        resolved_ids = EvaluationIds() if ids is None else ids

        frozen_evidence = tuple(evidence)
        frozen_standing = tuple(standing)
        frozen_delegations = tuple(delegations)
        frozen_approvals = tuple(approvals)
        frozen_context = tuple(context)

        candidate_consequence = Consequence(
            consequence_id=(
                resolved_ids.consequence_id
                or _generate_id(
                    self._config.id_factory,
                    IdentityKind.CONSEQUENCE,
                )
            ),
            idempotency_key=idempotency_key,
            action=action,
        )
        consequence = self._idempotency_registry.resolve(
            candidate_consequence
        )

        attempt = Attempt(
            attempt_id=(
                resolved_ids.attempt_id
                or _generate_id(
                    self._config.id_factory,
                    IdentityKind.ATTEMPT,
                )
            ),
            consequence=consequence,
        )

        decision = evaluate_attempt(
            decision_id=(
                resolved_ids.decision_id
                or _generate_id(
                    self._config.id_factory,
                    IdentityKind.DECISION,
                )
            ),
            attempt=attempt,
            rule=self._rule,
            evidence=frozen_evidence,
            standing=frozen_standing,
            delegations=frozen_delegations,
            approvals=frozen_approvals,
            context=frozen_context,
        )

        decision_proof = create_decision_proof(
            proof_id=(
                resolved_ids.decision_proof_id
                or _generate_id(
                    self._config.id_factory,
                    IdentityKind.DECISION_PROOF,
                )
            ),
            decision=decision,
            evidence=frozen_evidence,
            standing=frozen_standing,
            delegations=frozen_delegations,
            approvals=frozen_approvals,
            context=frozen_context,
        )

        warrant = Warrant(
            warrant_id=(
                resolved_ids.warrant_id
                or _generate_id(
                    self._config.id_factory,
                    IdentityKind.WARRANT,
                )
            ),
            schema_version="0.7",
            decision_proof=decision_proof,
        )

        return EvaluationResult(warrant=warrant)