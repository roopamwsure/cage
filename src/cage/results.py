from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from cage.core.adapter import AdapterExecutionResult
from cage.core.attempt import Attempt
from cage.core.capability import ExecutionCapability
from cage.core.consequence import Consequence
from cage.core.custody import (
    CapabilityMismatchError,
    validate_capability_for_custody,
)
from cage.core.decision import Decision, DecisionState
from cage.core.effect import Effect, EffectState
from cage.core.execution import ExecutionAttempt
from cage.core.verification import EffectVerificationResult
from cage.core.warrant import DecisionProof, EffectProof, Warrant
from cage.errors import CAGETypeError, CAGEValueError

__all__ = [
    "AssuranceResult",
    "Decision",
    "DecisionState",
    "Effect",
    "EffectState",
    "EvaluationResult",
    "ExecutionObservationOrigin",
    "ExecutionResult",
]


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


@dataclass(frozen=True, slots=True)
class AssuranceResult:
    """Immutable developer view of externally verified assurance."""

    execution: ExecutionResult
    warrant: Warrant

    def __post_init__(self) -> None:
        if not isinstance(self.execution, ExecutionResult):
            raise CAGETypeError(
                "execution must be an ExecutionResult"
            )

        if not isinstance(self.warrant, Warrant):
            raise CAGETypeError("warrant must be a Warrant")

        if self.warrant.effect_proof is None:
            raise CAGEValueError(
                "AssuranceResult requires a Warrant "
                "with an EffectProof"
            )

        if (
            self.warrant.decision_proof
            != self.execution.decision_proof
        ):
            raise CAGEValueError(
                "warrant decision proof does not match "
                "execution evaluation"
            )

        if (
            self.warrant.effect_proof.verification.adapter_result
            != self.execution.adapter_result
        ):
            raise CAGEValueError(
                "warrant effect proof does not match "
                "execution observation"
            )

    @property
    def decision(self) -> Decision:
        return self.execution.decision

    @property
    def decision_proof(self) -> DecisionProof:
        return self.execution.decision_proof

    @property
    def execution_attempt(self) -> ExecutionAttempt:
        return self.execution.execution_attempt

    @property
    def adapter_result(self) -> AdapterExecutionResult:
        return self.execution.adapter_result

    @property
    def observation_origin(self) -> ExecutionObservationOrigin:
        return self.execution.observation_origin

    @property
    def effect_proof(self) -> EffectProof:
        return cast(EffectProof, self.warrant.effect_proof)

    @property
    def effect(self) -> Effect:
        return self.effect_proof.effect

    @property
    def verification(self) -> EffectVerificationResult:
        return self.effect_proof.verification

    @property
    def consequence_id(self) -> str:
        return self.execution.consequence_id

    @property
    def idempotency_key(self) -> str:
        return self.execution.idempotency_key