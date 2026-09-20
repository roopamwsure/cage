from dataclasses import dataclass
from enum import StrEnum

from cage.core.adapter import AdapterExecutionResult
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
from cage.core.consequence import Consequence
from cage.core.custody import (
    CapabilityMismatchError,
    validate_capability_for_custody,
)
from cage.core.decision import Decision
from cage.core.execution import ExecutionAttempt
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


class ExecutionObservationOrigin(StrEnum):
    ADAPTER = "adapter"
    SDK_RECOVERY = "sdk_recovery"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable developer view of an execution observation."""

    evaluation: EvaluationResult
    capability: ExecutionCapability
    adapter_result: AdapterExecutionResult
    observation_origin: ExecutionObservationOrigin

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation, EvaluationResult):
            raise CAGETypeError(
                "evaluation must be an EvaluationResult"
            )

        if not isinstance(self.capability, ExecutionCapability):
            raise CAGETypeError(
                "capability must be an ExecutionCapability"
            )

        if not isinstance(
            self.adapter_result,
            AdapterExecutionResult,
        ):
            raise CAGETypeError(
                "adapter_result must be an AdapterExecutionResult"
            )

        if not isinstance(
            self.observation_origin,
            ExecutionObservationOrigin,
        ):
            raise CAGETypeError(
                "observation_origin must be an "
                "ExecutionObservationOrigin"
            )

        if (
            self.adapter_result.execution_attempt.decision
            != self.evaluation.decision
        ):
            raise CAGEValueError(
                "adapter result decision does not match "
                "evaluation decision"
            )

        try:
            validate_capability_for_custody(
                decision=self.evaluation.decision,
                capability=self.capability,
            )
        except CapabilityMismatchError as error:
            raise CAGEValueError(
                "capability does not match evaluation decision"
            ) from error

    @property
    def decision(self) -> Decision:
        return self.evaluation.decision

    @property
    def decision_proof(self) -> DecisionProof:
        return self.evaluation.decision_proof

    @property
    def execution_attempt(self) -> ExecutionAttempt:
        return self.adapter_result.execution_attempt

    @property
    def consequence_id(self) -> str:
        return self.evaluation.consequence_id

    @property
    def idempotency_key(self) -> str:
        return self.evaluation.idempotency_key
