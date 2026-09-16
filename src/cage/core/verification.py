from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from cage.core.adapter import AdapterExecutionResult
from cage.core.consequence import Consequence
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