from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from cage.core.adapter import AdapterExecutionResult
from cage.core.consequence import Consequence
from cage.core.effect import Effect, EffectState
from cage.core.execution import ExecutionAttempt

def _require_non_empty(
    value: str,
    field_name: str,
) -> None:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    if not value.strip():
        raise ValueError(
            f"{field_name} must not be empty"
        )


def _freeze_references(
    references: Sequence[str],
    field_name: str,
) -> tuple[str, ...]:
    if isinstance(references, str):
        raise TypeError(
            f"{field_name} must be a sequence of strings"
        )

    if not isinstance(references, Sequence):
        raise TypeError(
            f"{field_name} must be a sequence of strings"
        )

    frozen = tuple(references)

    for reference in frozen:
        _require_non_empty(
            reference,
            field_name,
        )

    return frozen


class VerificationState(StrEnum):
    VERIFIED_BOUND = "verified_bound"
    VERIFIED_NO_BIND = "verified_no_bind"
    INCONCLUSIVE = "inconclusive"


class VerificationResultMismatchError(ValueError):
    """Raised when verification refers to another adapter result."""


@dataclass(frozen=True, slots=True)
class EffectVerificationResult:
    verification_id: str
    adapter_result: AdapterExecutionResult
    state: VerificationState
    references: Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_non_empty(
            self.verification_id,
            "verification_id",
        )

        if not isinstance(
            self.adapter_result,
            AdapterExecutionResult,
        ):
            raise TypeError(
                "adapter_result must be an AdapterExecutionResult"
            )

        if not isinstance(
            self.state,
            VerificationState,
        ):
            raise TypeError(
                "state must be a VerificationState"
            )

        frozen_references = _freeze_references(
            self.references,
            "references",
        )

        if (
            self.state
            in {
                VerificationState.VERIFIED_BOUND,
                VerificationState.VERIFIED_NO_BIND,
            }
            and not frozen_references
        ):
            raise ValueError(
                f"{self.state.value} requires verification references"
            )

        object.__setattr__(
            self,
            "references",
            frozen_references,
        )

    @property
    def execution_attempt(self) -> ExecutionAttempt:
        return self.adapter_result.execution_attempt

    @property
    def consequence(self) -> Consequence:
        return self.execution_attempt.consequence


@runtime_checkable
class EffectVerifier(Protocol):
    def verify(
        self,
        *,
        adapter_result: AdapterExecutionResult,
    ) -> EffectVerificationResult:
        ...


def reconcile_effect_verification(
    *,
    adapter_result: AdapterExecutionResult,
    verifier: EffectVerifier,
) -> EffectVerificationResult:
    if not isinstance(
        adapter_result,
        AdapterExecutionResult,
    ):
        raise TypeError(
            "adapter_result must be an AdapterExecutionResult"
        )

    if not isinstance(
        verifier,
        EffectVerifier,
    ):
        raise TypeError(
            "verifier must satisfy EffectVerifier"
        )

    verification = verifier.verify(
        adapter_result=adapter_result,
    )

    if not isinstance(
        verification,
        EffectVerificationResult,
    ):
        raise TypeError(
            "verifier must return an EffectVerificationResult"
        )

    if verification.adapter_result != adapter_result:
        raise VerificationResultMismatchError(
            "verification adapter_result does not match "
            "reconciled adapter_result"
        )

    return verification


def create_effect_from_verification(
    *,
    effect_id: str,
    verification: EffectVerificationResult,
) -> Effect:
    if not isinstance(
        verification,
        EffectVerificationResult,
    ):
        raise TypeError(
            "verification must be an EffectVerificationResult"
        )

    if verification.state is VerificationState.VERIFIED_BOUND:
        effect_state = EffectState.BOUND

    elif verification.state is VerificationState.VERIFIED_NO_BIND:
        effect_state = EffectState.NO_BIND

    else:
        effect_state = EffectState.EFFECT_UNKNOWN

    return Effect(
        effect_id=effect_id,
        state=effect_state,
        consequence=verification.consequence,
        verification_refs=verification.references,
    )