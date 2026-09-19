class CAGEError(Exception):
    """Base class for public CAGE SDK errors."""


class CAGETypeError(CAGEError, TypeError):
    """Raised when an SDK argument has an invalid type."""


class CAGEValueError(CAGEError, ValueError):
    """Raised when an SDK argument has an invalid value."""