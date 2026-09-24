"""Detached, inspection-only projections of native Warrants."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import json

from cage.core._json import freeze_json_value
from cage.core.decision import DecisionState
from cage.core.warrant import Warrant
from cage.errors import CAGETypeError, CAGEValueError, WarrantExportError
from cage.results import EvaluationResult


class WarrantDisclosure(StrEnum):
    SUMMARY = "summary"
    FULL = "full"


def _copy_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _copy_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_copy_json(item) for item in value]
    return value


def _check_depth(value: object) -> None:
    pending = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > 64:
            raise WarrantExportError("Warrant exceeds the format nesting depth of 64")
        if isinstance(current, Mapping):
            pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, (list, tuple)):
            pending.extend((item, depth + 1) for item in current)


@dataclass(frozen=True, slots=True)
class PortableWarrant:
    """Immutable detached decision snapshot; never an execution capability."""

    _data: object

    def __post_init__(self) -> None:
        try:
            _check_depth(self._data)
            object.__setattr__(self, "_data", freeze_json_value(_copy_json(self._data)))
        except WarrantExportError:
            raise
        except (TypeError, ValueError, RecursionError) as error:
            raise WarrantExportError("Warrant contains unsupported JSON data") from error

    def to_dict(self) -> dict[str, object]:
        return _copy_json(self._data)  # type: ignore[return-value]

    def to_json(self, *, indent: int | None = 2) -> str:
        if indent is not None and (type(indent) is not int or not 0 <= indent <= 8):
            raise CAGEValueError("indent must be None or an integer from 0 to 8")
        serialized = json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)
        if len(serialized.encode("utf-8")) > 8 * 1024 * 1024:
            raise WarrantExportError("Warrant exceeds the 8 MiB format limit")
        return serialized

    @property
    def format_version(self) -> str:
        return self._data["format_version"]  # type: ignore[index]

    @property
    def disclosure(self) -> WarrantDisclosure:
        return WarrantDisclosure(self._data["disclosure"]["profile"])  # type: ignore[index]

    @property
    def warrant_id(self) -> str:
        return self._data["warrant"]["warrant_id"]  # type: ignore[index]

    @property
    def schema_version(self) -> str:
        return self._data["warrant"]["schema_version"]  # type: ignore[index]

    @property
    def consequence_id(self) -> str:
        return self._data["consequence"]["consequence_id"]  # type: ignore[index]

    @property
    def decision_state(self) -> DecisionState:
        return DecisionState(self._data["decision"]["state"])  # type: ignore[index]

    @property
    def effect_state(self) -> None:
        return None

    @property
    def execution_attempt_id(self) -> None:
        return None

    @property
    def previous_warrant_id(self) -> str | None:
        return self._data["warrant"]["previous_warrant_id"]  # type: ignore[index]

    @property
    def observation_origin(self) -> None:
        return None


def export_warrant(
    source: Warrant | EvaluationResult,
    *,
    disclosure: WarrantDisclosure = WarrantDisclosure.SUMMARY,
) -> PortableWarrant:
    """Export a decision-only Warrant; assured paths require a later slice."""

    if not isinstance(disclosure, WarrantDisclosure):
        raise CAGETypeError("disclosure must be a WarrantDisclosure")
    if not isinstance(source, (Warrant, EvaluationResult)):
        raise CAGETypeError("source must be a Warrant or EvaluationResult")
    warrant = source.warrant if isinstance(source, EvaluationResult) else source
    if warrant.effect_proof is not None:
        raise WarrantExportError("only decision-only Warrants are supported yet")

    proof = warrant.decision_proof
    decision = proof.decision
    attempt = decision.attempt
    consequence = attempt.consequence
    action = consequence.action
    summary = disclosure is WarrantDisclosure.SUMMARY
    refs = ("evidence", "standing", "delegation", "approval", "context")
    omitted = [
        "consequence.idempotency_key", "action.principal_id",
        "action.agent_id", "action.resource_id",
        "action.requested_effect.parameters",
    ] if summary else []
    if summary and decision.permitted_effect is not None:
        omitted.append("decision.permitted_effect.parameters")
    if summary:
        omitted.extend(f"decision_proof.{name}_refs" for name in refs)

    payload: dict[str, object] = {
        "format": "cage.warrant",
        "format_version": "1",
        "disclosure": {"profile": disclosure.value, "omitted_fields": omitted},
        "warrant": {
            "warrant_id": warrant.warrant_id,
            "schema_version": warrant.schema_version,
            "previous_warrant_id": warrant.previous_warrant_id,
        },
        "consequence": {
            "consequence_id": consequence.consequence_id,
            "action_id": action.action_id,
            "idempotency_key": None if summary else consequence.idempotency_key,
        },
        "action": {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "principal_id": None if summary else action.principal.principal_id,
            "agent_id": None if summary else action.agent.agent_id,
            "resource_id": None if summary else action.resource.resource_id,
            "requested_effect": {
                "parameters": None if summary else _copy_json(action.requested_effect.parameters),
            },
        },
        "evaluation_attempt": {
            "attempt_id": attempt.attempt_id,
            "consequence_id": consequence.consequence_id,
            "previous_attempt_id": attempt.previous_attempt_id,
        },
        "decision": {
            "decision_id": decision.decision_id,
            "attempt_id": attempt.attempt_id,
            "state": decision.state.value,
            "permitted_effect": (
                None if decision.permitted_effect is None else {
                    "parameters": None if summary else _copy_json(decision.permitted_effect.parameters),
                }
            ),
        },
        "decision_proof": {
            "proof_id": proof.proof_id,
            "decision_id": decision.decision_id,
            **{f"{name}_refs": None if summary else list(getattr(proof, f"{name}_refs")) for name in refs},
            "reference_counts": {name: len(getattr(proof, f"{name}_refs")) for name in refs},
        },
        "execution_attempt": None,
        "adapter_result": None,
        "verification": None,
        "effect": None,
        "effect_proof": None,
    }
    try:
        _check_depth(payload)
        frozen = freeze_json_value(payload)
        document = PortableWarrant(frozen)
        document.to_json(indent=None)
    except WarrantExportError:
        raise
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise WarrantExportError("Warrant contains unsupported JSON data") from error
    return document
