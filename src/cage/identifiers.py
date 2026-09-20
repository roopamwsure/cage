from collections.abc import Callable
from dataclasses import dataclass, fields
from enum import Enum
from typing import TypeAlias
from uuid import uuid4

from cage.errors import (
    CAGETypeError,
    CAGEValueError,
    IdentifierGenerationError,
)


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


def _validate_optional_ids(instance: object) -> None:
    for field in fields(instance):
        value = getattr(instance, field.name)

        if value is None:
            continue

        if not isinstance(value, str):
            raise CAGETypeError(f"{field.name} must be a string or None")

        if not value.strip():
            raise CAGEValueError(f"{field.name} must not be blank")


def _generate_id(id_factory: IdFactory, kind: IdentityKind) -> str:
    try:
        generated = id_factory(kind)
    except Exception as error:
        raise IdentifierGenerationError(kind) from error

    if not isinstance(generated, str):
        raise CAGETypeError(
            f"id_factory must return a string for {kind.value}"
        )

    if not generated.strip():
        raise CAGEValueError(
            f"id_factory must return a nonblank string for {kind.value}"
        )

    return generated


@dataclass(frozen=True, slots=True)
class EvaluationIds:
    consequence_id: str | None = None
    attempt_id: str | None = None
    decision_id: str | None = None
    decision_proof_id: str | None = None
    warrant_id: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_ids(self)


@dataclass(frozen=True, slots=True)
class AssuranceIds:
    effect_id: str | None = None
    effect_proof_id: str | None = None
    warrant_id: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_ids(self)


def uuid_id(kind: IdentityKind) -> str:
    """Generate an opaque record identifier for an identity namespace."""
    if not isinstance(kind, IdentityKind):
        raise CAGETypeError("kind must be an IdentityKind")

    return f"{kind.value}_{uuid4().hex}"