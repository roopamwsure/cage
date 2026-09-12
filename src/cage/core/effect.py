from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from cage.core.consequence import Consequence


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


class EffectState(StrEnum):
    BOUND = "bound"
    NO_BIND = "no_bind"
    EFFECT_UNKNOWN = "effect_unknown"


@dataclass(frozen=True, slots=True)
class Effect:
    effect_id: str
    state: EffectState
    consequence: Consequence
    verification_refs: Sequence[str] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.effect_id, "effect_id")

        if not isinstance(self.state, EffectState):
            raise TypeError("state must be an EffectState")

        if not isinstance(self.consequence, Consequence):
            raise TypeError("consequence must be a Consequence")

        if isinstance(self.verification_refs, str):
            raise TypeError(
                "verification_refs must be a sequence of strings"
            )

        if not isinstance(self.verification_refs, Sequence):
            raise TypeError(
                "verification_refs must be a sequence of strings"
            )

        refs = tuple(self.verification_refs)

        for ref in refs:
            _require_non_empty(ref, "verification_ref")

        if (
            self.state in {EffectState.BOUND, EffectState.NO_BIND}
            and not refs
        ):
            raise ValueError(
                "BOUND and NO_BIND require verification references"
            )

        object.__setattr__(self, "verification_refs", refs)