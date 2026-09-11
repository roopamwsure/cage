from collections.abc import Mapping
from math import isfinite
from types import MappingProxyType


def freeze_json_value(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value

    if isinstance(value, list):
        return tuple(freeze_json_value(item) for item in value)

    if isinstance(value, Mapping):
        frozen = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")

            frozen[key] = freeze_json_value(item)

        return MappingProxyType(frozen)

    raise TypeError("value must contain only JSON-compatible data")