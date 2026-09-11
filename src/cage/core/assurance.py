from collections.abc import Mapping
from dataclasses import dataclass

from cage.core._json import freeze_json_value


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    evidence_type: str
    subject: str
    source: str
    data: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty(self.evidence_id, "evidence_id")
        _require_non_empty(self.evidence_type, "evidence_type")
        _require_non_empty(self.subject, "subject")
        _require_non_empty(self.source, "source")

        if not isinstance(self.data, Mapping):
            raise TypeError("data must be a mapping")

        frozen_data = freeze_json_value(self.data)
        object.__setattr__(self, "data", frozen_data)


@dataclass(frozen=True, slots=True)
class Standing:
    standing_id: str
    standing_type: str
    subject: str
    source: str
    attributes: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty(self.standing_id, "standing_id")
        _require_non_empty(self.standing_type, "standing_type")
        _require_non_empty(self.subject, "subject")
        _require_non_empty(self.source, "source")

        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")

        frozen_attributes = freeze_json_value(self.attributes)
        object.__setattr__(self, "attributes", frozen_attributes)


@dataclass(frozen=True, slots=True)
class Delegation:
    delegation_id: str
    delegator: str
    delegatee: str
    source: str
    scope: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty(self.delegation_id, "delegation_id")
        _require_non_empty(self.delegator, "delegator")
        _require_non_empty(self.delegatee, "delegatee")
        _require_non_empty(self.source, "source")

        if not isinstance(self.scope, Mapping):
            raise TypeError("scope must be a mapping")

        frozen_scope = freeze_json_value(self.scope)
        object.__setattr__(self, "scope", frozen_scope)


@dataclass(frozen=True, slots=True)
class Approval:
    approval_id: str
    approval_type: str
    approver: str
    subject: str
    source: str
    scope: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty(self.approval_id, "approval_id")
        _require_non_empty(self.approval_type, "approval_type")
        _require_non_empty(self.approver, "approver")
        _require_non_empty(self.subject, "subject")
        _require_non_empty(self.source, "source")

        if not isinstance(self.scope, Mapping):
            raise TypeError("scope must be a mapping")

        frozen_scope = freeze_json_value(self.scope)
        object.__setattr__(self, "scope", frozen_scope)


@dataclass(frozen=True, slots=True)
class Context:
    context_id: str
    context_type: str
    source: str
    values: Mapping[str, object]

    def __post_init__(self) -> None:
        _require_non_empty(self.context_id, "context_id")
        _require_non_empty(self.context_type, "context_type")
        _require_non_empty(self.source, "source")

        if not isinstance(self.values, Mapping):
            raise TypeError("values must be a mapping")

        frozen_values = freeze_json_value(self.values)
        object.__setattr__(self, "values", frozen_values)