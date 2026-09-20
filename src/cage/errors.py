from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cage.identifiers import IdentityKind


class CAGEError(Exception):
    """Base class for public CAGE SDK errors."""


class CAGETypeError(CAGEError, TypeError):
    """Raised when an SDK argument has an invalid type."""


class CAGEValueError(CAGEError, ValueError):
    """Raised when an SDK argument has an invalid value."""


class IdentifierGenerationError(CAGEError):
    """Raised when a configured identifier factory cannot produce an ID."""

    def __init__(self, kind: "IdentityKind") -> None:
        self.kind = kind
        super().__init__(f"failed to generate {kind.value} identifier")