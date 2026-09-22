from collections.abc import Callable, Sequence
from dataclasses import dataclass
from threading import Lock

from cage.config import CAGEConfig
from cage.core.action import Action, RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    AdapterExecutionState,
    EffectAdapter,
)
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
from cage.core.consequence import Consequence
from cage.core.custody import (
    AdapterResultMismatchError as CoreAdapterResultMismatchError,
    execute_under_custody,
)
from cage.core.evaluation import (
    EvaluationRule,
    evaluate_attempt,
)
from cage.core.execution import ExecutionAttempt
from cage.core.idempotency import (
    IdempotencyConflictError,
    IdempotencyRegistry,
)
from cage.core.replay import create_replay_attempt
from cage.core.warrant import Warrant, create_decision_proof
from cage.errors import (
    AdapterContractError,
    AdapterInvocationError,
    AdapterResultMismatchError,
    CAGETypeError,
    CAGEValueError,
    DuplicateExecutionError,
)
from cage.identifiers import (
    EvaluationIds,
    IdentityKind,
    _generate_id,
)
from cage.inputs import CAGEInputs
from cage.results import (
    EvaluationResult,
    ExecutionObservationOrigin,
    ExecutionResult,
)


@dataclass(slots=True)
class _DispatchRecord:
    execution_attempt: ExecutionAttempt
    dispatched: bool = False
    execution: ExecutionResult | None = None


class _AdapterCallbackFailure(Exception):
    def __init__(self, error: Exception) -> None:
        self.error = error
        super().__init__("adapter callback failed")


class _DispatchTrackingAdapter:
    def __init__(
        self,
        *,
        adapter: EffectAdapter,
        mark_dispatched: Callable[[], None],
    ) -> None:
        self._adapter = adapter
        self._mark_dispatched = mark_dispatched

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self._mark_dispatched()

        try:
            return self._adapter.execute(
                execution_attempt=execution_attempt,
                effect=effect,
                capability=capability,
            )
        except Exception as error:
            raise _AdapterCallbackFailure(error) from error


def _create_sdk_recovery_execution(
    *,
    evaluation: EvaluationResult,
    capability: ExecutionCapability,
    execution_attempt: ExecutionAttempt,
    result_id: str,
) -> ExecutionResult:
    recovery_adapter_result = AdapterExecutionResult(
        result_id=result_id,
        execution_attempt=execution_attempt,
        state=AdapterExecutionState.UNKNOWN,
        references=(
            "urn:cage:sdk:recovery-observation",
        ),
    )
    return ExecutionResult(
        evaluation=evaluation,
        capability=capability,
        adapter_result=recovery_adapter_result,
        observation_origin=ExecutionObservationOrigin.SDK_RECOVERY,
    )


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
        "_dispatch_records",
        "_idempotency_registry",
        "_inputs",
        "_rule",
        "_state_lock",
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
        self._dispatch_records: dict[str, _DispatchRecord] = {}
        self._state_lock = Lock()

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

            with self._state_lock:
                consequence = self._idempotency_registry.resolve(
                    candidate_consequence
                )
        else:
            candidate_consequence = Consequence(
                consequence_id=previous.consequence_id,
                idempotency_key=idempotency_key,
                action=action,
            )

            with self._state_lock:
                self._idempotency_registry.resolve(
                    previous.consequence
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

    def execute(
        self,
        evaluation: EvaluationResult,
        *,
        adapter: EffectAdapter,
        capability: ExecutionCapability,
        execution_attempt_id: str | None = None,
    ) -> ExecutionResult:
        if not isinstance(evaluation, EvaluationResult):
            raise CAGETypeError(
                "evaluation must be an EvaluationResult"
            )

        if not isinstance(capability, ExecutionCapability):
            raise CAGETypeError(
                "capability must be an ExecutionCapability"
            )

        if not isinstance(adapter, EffectAdapter):
            raise CAGETypeError(
                "adapter must satisfy EffectAdapter"
            )

        if (
            execution_attempt_id is not None
            and not isinstance(execution_attempt_id, str)
        ):
            raise CAGETypeError(
                "execution_attempt_id must be a string or None"
            )

        if (
            isinstance(execution_attempt_id, str)
            and not execution_attempt_id.strip()
        ):
            raise CAGEValueError(
                "execution_attempt_id must not be blank"
            )

        resolved_execution_attempt_id = (
            _generate_id(
                self._config.id_factory,
                IdentityKind.EXECUTION_ATTEMPT,
            )
            if execution_attempt_id is None
            else execution_attempt_id
        )

        recovery_result_id = _generate_id(
            self._config.id_factory,
            IdentityKind.ADAPTER_RESULT,
        )

        execution_attempt = ExecutionAttempt(
            execution_attempt_id=resolved_execution_attempt_id,
            decision=evaluation.decision,
        )

        with self._state_lock:
            canonical_consequence = (
                self._idempotency_registry.resolve(
                    evaluation.consequence
                )
            )
            consequence_id = canonical_consequence.consequence_id
            existing_record = self._dispatch_records.get(
                consequence_id
            )

            if existing_record is not None:
                raise DuplicateExecutionError(
                    execution_attempt=(
                        existing_record.execution_attempt
                    ),
                    consequence_id=consequence_id,
                    execution=existing_record.execution,
                )

            record = _DispatchRecord(
                execution_attempt=execution_attempt
            )
            self._dispatch_records[consequence_id] = record

        def mark_dispatched() -> None:
            with self._state_lock:
                record.dispatched = True

        tracking_adapter = _DispatchTrackingAdapter(
            adapter=adapter,
            mark_dispatched=mark_dispatched,
        )

        try:
            adapter_result = execute_under_custody(
                execution_attempt=execution_attempt,
                capability=capability,
                adapter=tracking_adapter,
            )
        except _AdapterCallbackFailure as failure:
            recovery_execution = _create_sdk_recovery_execution(
                evaluation=evaluation,
                capability=capability,
                execution_attempt=execution_attempt,
                result_id=recovery_result_id,
            )

            with self._state_lock:
                record.execution = recovery_execution

            raise AdapterInvocationError(
                "adapter invocation failed after dispatch began",
                execution=recovery_execution,
            ) from failure.error
        except CoreAdapterResultMismatchError as error:
            recovery_execution = _create_sdk_recovery_execution(
                evaluation=evaluation,
                capability=capability,
                execution_attempt=execution_attempt,
                result_id=recovery_result_id,
            )

            with self._state_lock:
                record.execution = recovery_execution

            raise AdapterResultMismatchError(
                "adapter result refers to a different execution attempt",
                execution=recovery_execution,
            ) from error
        except TypeError as error:
            with self._state_lock:
                dispatched = record.dispatched

            if not dispatched:
                raise

            recovery_execution = _create_sdk_recovery_execution(
                evaluation=evaluation,
                capability=capability,
                execution_attempt=execution_attempt,
                result_id=recovery_result_id,
            )

            with self._state_lock:
                record.execution = recovery_execution

            raise AdapterContractError(
                "adapter returned an invalid result after dispatch began",
                execution=recovery_execution,
            ) from error
        except BaseException:
            with self._state_lock:
                dispatched = record.dispatched

                if not dispatched:
                    current_record = self._dispatch_records.get(
                        consequence_id
                    )

                    if current_record is record:
                        del self._dispatch_records[consequence_id]

            if dispatched:
                recovery_execution = _create_sdk_recovery_execution(
                    evaluation=evaluation,
                    capability=capability,
                    execution_attempt=execution_attempt,
                    result_id=recovery_result_id,
                )

                with self._state_lock:
                    record.execution = recovery_execution

            raise

        try:
            execution = ExecutionResult(
                evaluation=evaluation,
                capability=capability,
                adapter_result=adapter_result,
                observation_origin=(
                    ExecutionObservationOrigin.ADAPTER
                ),
            )
        except BaseException:
            recovery_execution = _create_sdk_recovery_execution(
                evaluation=evaluation,
                capability=capability,
                execution_attempt=execution_attempt,
                result_id=recovery_result_id,
            )

            with self._state_lock:
                record.execution = recovery_execution

            raise

        with self._state_lock:
            record.execution = execution

        return execution
