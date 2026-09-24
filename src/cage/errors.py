from typing import TYPE_CHECKING

from cage.core.custody import (
    AdapterResultMismatchError as CoreAdapterResultMismatchError,
)
from cage.core.verification import (
    VerificationResultMismatchError as CoreVerificationResultMismatchError,
)

if TYPE_CHECKING:
    from cage.core.execution import ExecutionAttempt
    from cage.core.verification import EffectVerificationResult
    from cage.identifiers import IdentityKind
    from cage.results import AssuranceResult, ExecutionResult


class CAGEError(Exception):
    """Base class for public CAGE SDK errors."""


class CAGETypeError(CAGEError, TypeError):
    """Raised when an SDK argument has an invalid type."""


class CAGEValueError(CAGEError, ValueError):
    """Raised when an SDK argument has an invalid value."""


class WarrantExportError(CAGEValueError):
    """Raised when a native Warrant cannot be safely exported."""


class WarrantFormatError(CAGEValueError):
    """Raised for an invalid portable Warrant representation."""


class UnsupportedWarrantVersionError(WarrantFormatError):
    """Raised for a portable format version this SDK cannot read."""


class IdentifierGenerationError(CAGEError):
    """Raised when a configured identifier factory cannot produce an ID."""

    def __init__(self, kind: "IdentityKind") -> None:
        self.kind = kind
        super().__init__(
            f"failed to generate {kind.value} identifier"
        )


class ExecutionError(CAGEError):
    """Base class for facade failures tied to an execution."""

    def __init__(
        self,
        message: str,
        *,
        execution: "ExecutionResult",
        previous: "AssuranceResult | None" = None,
    ) -> None:
        self.execution = execution
        self.previous = previous
        super().__init__(message)


class AdapterInvocationError(ExecutionError):
    """Raised when an adapter callback raises after dispatch begins."""


class AdapterContractError(ExecutionError):
    """Raised when an adapter returns an invalid result after dispatch."""


class AdapterResultMismatchError(
    ExecutionError,
    CoreAdapterResultMismatchError,
):
    """Raised when an adapter result refers to another execution."""


class VerifierInvocationError(ExecutionError):
    """Raised when an effect verifier callback fails."""


class VerifierContractError(ExecutionError):
    """Raised when an effect verifier returns an invalid result."""


class VerificationResultMismatchError(
    ExecutionError,
    CoreVerificationResultMismatchError,
):
    """Raised when verification refers to another adapter result."""


class AssuranceAssemblyError(ExecutionError):
    """Raised when assembly fails after a valid verification."""

    def __init__(
        self,
        message: str,
        *,
        execution: "ExecutionResult",
        verification: "EffectVerificationResult",
        stage: str,
        previous: "AssuranceResult | None" = None,
    ) -> None:
        self.stage = stage
        self.verification = verification
        super().__init__(message, execution=execution, previous=previous)


class DuplicateExecutionError(CAGEError, RuntimeError):
    """Raised when a Consequence is already reserved for execution."""

    def __init__(
        self,
        *,
        execution_attempt: "ExecutionAttempt",
        consequence_id: str,
        execution: "ExecutionResult | None" = None,
    ) -> None:
        self.execution_attempt = execution_attempt
        self.consequence_id = consequence_id
        self.execution = execution

        super().__init__(
            "execution dispatch is already reserved for "
            f"consequence {consequence_id}"
        )


class DuplicateVerificationError(CAGEError, RuntimeError):
    """Raised when first verification is in progress or completed."""

    def __init__(
        self,
        *,
        execution: "ExecutionResult",
        assurance: "AssuranceResult | None",
    ) -> None:
        self.execution = execution
        self.assurance = assurance
        super().__init__(
            "first verification is already reserved for "
            f"execution {execution.execution_attempt.execution_attempt_id}"
        )


class DuplicateReconciliationError(CAGEError, RuntimeError):
    """Raised when a predecessor has an in-progress or completed successor."""

    def __init__(
        self,
        *,
        previous: "AssuranceResult",
        assurance: "AssuranceResult | None",
    ) -> None:
        self.previous = previous
        self.assurance = assurance
        super().__init__(
            "reconciliation is already reserved for "
            f"warrant {previous.warrant.warrant_id}"
        )
