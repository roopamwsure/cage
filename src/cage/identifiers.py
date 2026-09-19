from collections.abc import Callable
from enum import Enum
from typing import TypeAlias
from uuid import uuid4

from cage.errors import CAGETypeError


class IdentityKind(str, Enum):
    ACTION = "action"
    CONSEQUENCE = "consequence"
    ATTEMPT = "attempt"
    DECISION = "decision"
    DECISION_PROOF = "decision_proof"
    EXECUTION_ATTEMPT = "execution_attempt"
    ADAPTER_RESULT = "adapter_result"
    VERIFICATION = "verification"
    EFFECT = "effect"
    EFFECT_PROOF = "effect_proof"
    WARRANT = "warrant"
    EVIDENCE = "evidence"
    STANDING = "standing"
    DELEGATION = "delegation"
    APPROVAL = "approval"
    CONTEXT = "context"


IdFactory: TypeAlias = Callable[[IdentityKind], str]


def uuid_id(kind: IdentityKind) -> str:
    """Generate an opaque record identifier for an identity namespace."""
    if not isinstance(kind, IdentityKind):
        raise CAGETypeError("kind must be an IdentityKind")

    return f"{kind.value}_{uuid4().hex}"