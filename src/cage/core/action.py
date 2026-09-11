from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

from cage.core.identity import Agent, Principal, Resource


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _freeze_json_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value

    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)

    if isinstance(value, Mapping):
        frozen = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "requested-effect parameter keys must be strings"
                )

            frozen[key] = _freeze_json_value(item)

        return MappingProxyType(frozen)

    raise TypeError(
        "requested-effect parameters must contain only JSON-compatible values"
    )


@dataclass(frozen=True, slots=True)
class RequestedEffect:
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a mapping")

        frozen_parameters = _freeze_json_value(self.parameters)
        object.__setattr__(self, "parameters", frozen_parameters)


@dataclass(frozen=True, slots=True)
class Action:
    action_id: str
    action_type: str
    principal: Principal
    agent: Agent
    resource: Resource
    requested_effect: RequestedEffect

    def __post_init__(self) -> None:
        _require_non_empty(self.action_id, "action_id")
        _require_non_empty(self.action_type, "action_type")

        if not isinstance(self.principal, Principal):
            raise TypeError("principal must be a Principal")

        if not isinstance(self.agent, Agent):
            raise TypeError("agent must be an Agent")

        if not isinstance(self.resource, Resource):
            raise TypeError("resource must be a Resource")

        if not isinstance(self.requested_effect, RequestedEffect):
            raise TypeError("requested_effect must be a RequestedEffect")