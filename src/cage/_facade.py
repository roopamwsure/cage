from cage.config import CAGEConfig
from cage.core.evaluation import EvaluationRule
from cage.core.idempotency import IdempotencyRegistry
from cage.errors import CAGETypeError
from cage.inputs import CAGEInputs


class CAGE:
    """High-level orchestrator for the CAGE lifecycle."""

    __slots__ = (
        "_config",
        "_idempotency_registry",
        "_inputs",
        "_rule",
    )

    def __init__(
        self,
        *,
        rule: EvaluationRule,
        config: CAGEConfig | None = None,
    ) -> None:
        if not callable(rule):
            raise CAGETypeError("rule must be callable")

        if config is not None and not isinstance(config, CAGEConfig):
            raise CAGETypeError(
                "config must be a CAGEConfig or None"
            )

        resolved_config = CAGEConfig() if config is None else config

        self._rule = rule
        self._config = resolved_config
        self._inputs = CAGEInputs(
            id_factory=resolved_config.id_factory
        )
        self._idempotency_registry = IdempotencyRegistry()

    @property
    def config(self) -> CAGEConfig:
        return self._config

    @property
    def inputs(self) -> CAGEInputs:
        return self._inputs