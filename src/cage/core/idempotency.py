from collections.abc import Mapping

from cage.core.consequence import Consequence


class IdempotencyConflictError(ValueError):
    pass


def _semantic_value(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                (
                    key,
                    _semantic_value(item),
                )
                for key, item in value.items()
            )
        )

    if isinstance(value, tuple):
        return tuple(_semantic_value(item) for item in value)

    return value

def _consequence_semantics(
    consequence: Consequence,
) -> tuple[object, ...]:
    action = consequence.action

    return (
        action.action_type,
        action.principal.principal_id,
        action.resource.resource_id,
        _semantic_value(action.requested_effect.parameters),
    )

class IdempotencyRegistry:
    def __init__(self) -> None:
        self._consequences: dict[str, Consequence] = {}

    def resolve(self, consequence: Consequence) -> Consequence:
        if not isinstance(consequence, Consequence):
            raise TypeError("consequence must be a Consequence")

        existing = self._consequences.get(
            consequence.idempotency_key
        )

        if existing is None:
            self._consequences[
                consequence.idempotency_key
            ] = consequence
            return consequence

        if (
            _consequence_semantics(existing)
            != _consequence_semantics(consequence)
        ):
            raise IdempotencyConflictError(
                "idempotency key is already associated "
                "with a different consequence"
            )

        return existing