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
from cage.core.idempotency import (
    IdempotencyConflictError,
    IdempotencyRegistry,
)
from cage.core.replay import create_replay_attempt
from cage.core.warrant import Warrant, create_decision_proof
from cage.errors import CAGETypeError, CAGEValueError
from cage.identifiers import (
    EvaluationIds,
    IdentityKind,
    _generate_id,
)
from cage.inputs import CAGEInputs
from cage.results import EvaluationResult

def _validate_replay_ids(
    *,
    previous: EvaluationResult,
    ids: EvaluationIds,
) -> None:
    predecessor_ids = (
        (
            "attempt_id",
            ids.attempt_id,
            previous.attempt.attempt_id,
        ),
        (
            "decision_id",
            ids.decision_id,
            previous.decision.decision_id,
        ),
        (
            "decision_proof_id",
            ids.decision_proof_id,
            previous.decision_proof.proof_id,
        ),
        (
            "warrant_id",
            ids.warrant_id,
            previous.warrant.warrant_id,
        ),
    )

    for field_name, proposed_id, predecessor_id in predecessor_ids:
        if proposed_id is not None and proposed_id == predecessor_id:
            raise CAGEValueError(
                f"{field_name} must not reuse the previous "
                "evaluation identity"
            )

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
        previous: EvaluationResult | None = None,
        ids: EvaluationIds | None = None,
    ) -> EvaluationResult:
        if previous is not None and not isinstance(
            previous,
            EvaluationResult,
        ):
            raise CAGETypeError(
                "previous must be an EvaluationResult or None"
            )
        if (
            previous is not None
            and idempotency_key != previous.idempotency_key
        ):
            raise IdempotencyConflictError(
                "replay idempotency_key does not match "
                "the previous consequence"
            )

        if ids is not None and not isinstance(ids, EvaluationIds):
            raise CAGETypeError(
                "ids must be an EvaluationIds or None"
            )

        resolved_ids = EvaluationIds() if ids is None else ids
        if previous is not None:
            _validate_replay_ids(
                previous=previous,
                ids=resolved_ids,
            )

        frozen_evidence = tuple(evidence)
        frozen_standing = tuple(standing)
        frozen_delegations = tuple(delegations)
        frozen_approvals = tuple(approvals)
        frozen_context = tuple(context)

        if previous is None:
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
        else:
            self._idempotency_registry.resolve(
                previous.consequence
            )
            candidate_consequence = Consequence(
                consequence_id=previous.consequence_id,
                idempotency_key=idempotency_key,
                action=action,
            )
            consequence = self._idempotency_registry.resolve(
                candidate_consequence
            )

        attempt_id = (
            resolved_ids.attempt_id
            or _generate_id(
                self._config.id_factory,
                IdentityKind.ATTEMPT,
            )
        )

        if previous is None:
            attempt = Attempt(
                attempt_id=attempt_id,
                consequence=consequence,
            )
        else:
            attempt = create_replay_attempt(
                previous_attempt=previous.attempt,
                attempt_id=attempt_id,
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
            previous_warrant_id=(
                None
                if previous is None
                else previous.warrant.warrant_id
            ),
        )

        return EvaluationResult(warrant=warrant)
