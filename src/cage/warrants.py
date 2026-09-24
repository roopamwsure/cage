"""Detached, inspection-only projections of native Warrants."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import json

from cage.core._json import freeze_json_value
from cage.core.decision import DecisionState
from cage.core.effect import EffectState
from cage.core.warrant import Warrant
from cage.errors import (
    CAGETypeError, CAGEValueError, UnsupportedWarrantVersionError,
    WarrantExportError, WarrantFormatError,
)
from cage.results import AssuranceResult, EvaluationResult, ExecutionObservationOrigin


_RECOVERY_MARKER = "urn:cage:sdk:recovery-observation"


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
    """Immutable detached lifecycle snapshot; never an execution capability."""

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
    def effect_state(self) -> EffectState | None:
        effect = self._data["effect"]  # type: ignore[index]
        return None if effect is None else EffectState(effect["state"])

    @property
    def execution_attempt_id(self) -> str | None:
        attempt = self._data["execution_attempt"]  # type: ignore[index]
        return None if attempt is None else attempt["execution_attempt_id"]

    @property
    def previous_warrant_id(self) -> str | None:
        return self._data["warrant"]["previous_warrant_id"]  # type: ignore[index]

    @property
    def observation_origin(self) -> str | None:
        adapter = self._data["adapter_result"]  # type: ignore[index]
        return None if adapter is None else adapter["origin"]


def export_warrant(
    source: Warrant | EvaluationResult | AssuranceResult,
    *,
    disclosure: WarrantDisclosure = WarrantDisclosure.SUMMARY,
) -> PortableWarrant:
    """Export a detached, internally consistent lifecycle snapshot."""

    if not isinstance(disclosure, WarrantDisclosure):
        raise CAGETypeError("disclosure must be a WarrantDisclosure")
    if not isinstance(source, (Warrant, EvaluationResult, AssuranceResult)):
        raise CAGETypeError("source must be a Warrant, EvaluationResult, or AssuranceResult")
    warrant = source if isinstance(source, Warrant) else source.warrant

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

    effect_proof = warrant.effect_proof
    if effect_proof is not None:
        verification = effect_proof.verification
        adapter_result = verification.adapter_result
        execution_attempt = adapter_result.execution_attempt
        effect = effect_proof.effect
        if execution_attempt.decision != decision:
            raise WarrantExportError("execution decision does not match Warrant decision")
        if effect.consequence != consequence:
            raise WarrantExportError("Effect consequence does not match Warrant consequence")
        if verification.consequence != consequence:
            raise WarrantExportError("verification consequence does not match Warrant consequence")
        if isinstance(source, AssuranceResult):
            origin = source.observation_origin.value
        elif _RECOVERY_MARKER in adapter_result.references:
            origin = ExecutionObservationOrigin.SDK_RECOVERY.value
        else:
            origin = "unspecified"
        if origin == "sdk_recovery" and adapter_result.state.value != "unknown":
            raise WarrantExportError("SDK recovery observation must have unknown adapter state")
        if origin == "sdk_recovery" and _RECOVERY_MARKER not in adapter_result.references:
            raise WarrantExportError("SDK recovery observation requires recovery marker")
        if origin == "adapter" and _RECOVERY_MARKER in adapter_result.references:
            raise WarrantExportError("adapter observation contains SDK recovery marker")
        if summary:
            omitted.extend((
                "adapter_result.references", "verification.references", "effect.verification_refs",
            ))

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
    if effect_proof is not None:
        payload.update({
            "execution_attempt": {
                "execution_attempt_id": execution_attempt.execution_attempt_id,
                "decision_id": decision.decision_id,
                "previous_execution_attempt_id": execution_attempt.previous_execution_attempt_id,
            },
            "adapter_result": {
                "result_id": adapter_result.result_id,
                "execution_attempt_id": execution_attempt.execution_attempt_id,
                "state": adapter_result.state.value,
                "origin": origin,
                "references": None if summary else list(adapter_result.references),
                "reference_count": len(adapter_result.references),
            },
            "verification": {
                "verification_id": verification.verification_id,
                "adapter_result_id": adapter_result.result_id,
                "state": verification.state.value,
                "references": None if summary else list(verification.references),
                "reference_count": len(verification.references),
            },
            "effect": {
                "effect_id": effect.effect_id,
                "consequence_id": consequence.consequence_id,
                "state": effect.state.value,
                "verification_refs": None if summary else list(effect.verification_refs),
                "verification_ref_count": len(effect.verification_refs),
            },
            "effect_proof": {
                "proof_id": effect_proof.proof_id,
                "effect_id": effect.effect_id,
                "verification_id": verification.verification_id,
            },
        })
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


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise WarrantFormatError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> object:
    raise WarrantFormatError(f"nonfinite JSON number: {value}")


def _object(value: object, path: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise WarrantFormatError(f"{path} must be an object")
    extra = value.keys() - fields
    if extra:
        raise WarrantFormatError(f"{path} has unknown fields: {', '.join(sorted(extra))}")
    missing = fields - value.keys()
    if missing:
        raise WarrantFormatError(f"{path} missing fields: {', '.join(sorted(missing))}")
    return value


def _id(value: object, path: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise WarrantFormatError(f"{path} must be a nonblank string")


def _refs(value: object, path: str, *, summary: bool) -> int | None:
    if summary and value is None:
        return None
    if not isinstance(value, list):
        raise WarrantFormatError(f"{path} must be an array")
    for item in value:
        _id(item, path)
    return len(value)


def _count(value: object, path: str) -> None:
    if type(value) is not int or value < 0:
        raise WarrantFormatError(f"{path} must be a nonnegative integer")


def _link(value: object, target: object, path: str) -> None:
    if value != target:
        raise WarrantFormatError(f"{path} does not match its target")


def _validate_decoded(data: object) -> None:
    root = _object(data, "warrant document", {
        "format", "format_version", "disclosure", "warrant", "consequence", "action",
        "evaluation_attempt", "decision", "decision_proof", "execution_attempt",
        "adapter_result", "verification", "effect", "effect_proof",
    })
    if root["format"] != "cage.warrant":
        raise WarrantFormatError("format must be cage.warrant")
    if root["format_version"] != "1":
        raise UnsupportedWarrantVersionError("unsupported portable Warrant format version")
    disclosure = _object(root["disclosure"], "disclosure", {"profile", "omitted_fields"})
    if disclosure["profile"] not in ("summary", "full"):
        raise WarrantFormatError("invalid disclosure profile")
    summary = disclosure["profile"] == "summary"
    omitted = disclosure["omitted_fields"]
    if not isinstance(omitted, list) or any(not isinstance(x, str) for x in omitted):
        raise WarrantFormatError("disclosure.omitted_fields must be an array of strings")

    warrant = _object(root["warrant"], "warrant", {
        "warrant_id", "schema_version", "previous_warrant_id",
    })
    for name in ("warrant_id", "schema_version"):
        _id(warrant[name], "warrant." + name)
    _id(warrant["previous_warrant_id"], "warrant.previous_warrant_id", nullable=True)
    if warrant["previous_warrant_id"] == warrant["warrant_id"]:
        raise WarrantFormatError("warrant cannot link to itself")
    consequence = _object(root["consequence"], "consequence", {
        "consequence_id", "action_id", "idempotency_key",
    })
    action = _object(root["action"], "action", {
        "action_id", "action_type", "principal_id", "agent_id", "resource_id", "requested_effect",
    })
    for obj, names, path in (
        (consequence, ("consequence_id", "action_id"), "consequence"),
        (action, ("action_id", "action_type"), "action"),
    ):
        for name in names:
            _id(obj[name], path + "." + name)
    _link(consequence["action_id"], action["action_id"], "consequence.action_id")
    omitted_expected = [
        "consequence.idempotency_key", "action.principal_id", "action.agent_id",
        "action.resource_id", "action.requested_effect.parameters",
    ] if summary else []
    for obj, fields, path in (
        (consequence, ("idempotency_key",), "consequence"),
        (action, ("principal_id", "agent_id", "resource_id"), "action"),
    ):
        for name in fields:
            _id(obj[name], path + "." + name, nullable=summary)
            if summary and obj[name] is not None:
                raise WarrantFormatError(path + "." + name + " must be omitted")
    requested = _object(action["requested_effect"], "action.requested_effect", {"parameters"})
    _parameters(requested["parameters"], "action.requested_effect.parameters", summary)

    attempt = _object(root["evaluation_attempt"], "evaluation_attempt", {
        "attempt_id", "consequence_id", "previous_attempt_id",
    })
    _id(attempt["attempt_id"], "evaluation_attempt.attempt_id")
    _id(attempt["consequence_id"], "evaluation_attempt.consequence_id")
    _id(attempt["previous_attempt_id"], "evaluation_attempt.previous_attempt_id", nullable=True)
    _link(attempt["consequence_id"], consequence["consequence_id"], "evaluation_attempt.consequence_id")
    if attempt["attempt_id"] == attempt["previous_attempt_id"]:
        raise WarrantFormatError("evaluation_attempt cannot link to itself")

    decision = _object(root["decision"], "decision", {
        "decision_id", "attempt_id", "state", "permitted_effect",
    })
    _id(decision["decision_id"], "decision.decision_id")
    _link(decision["attempt_id"], attempt["attempt_id"], "decision.attempt_id")
    if decision["state"] not in tuple(state.value for state in DecisionState):
        raise WarrantFormatError("invalid decision state")
    if decision["state"] == DecisionState.NARROWED:
        permitted = _object(decision["permitted_effect"], "decision.permitted_effect", {"parameters"})
        _parameters(permitted["parameters"], "decision.permitted_effect.parameters", summary)
        if summary:
            omitted_expected.append("decision.permitted_effect.parameters")
    elif decision["permitted_effect"] is not None:
        raise WarrantFormatError("permitted_effect is only valid for narrowed decisions")

    proof = _object(root["decision_proof"], "decision_proof", {
        "proof_id", "decision_id", "evidence_refs", "standing_refs",
        "delegation_refs", "approval_refs", "context_refs", "reference_counts",
    })
    _id(proof["proof_id"], "decision_proof.proof_id")
    _link(proof["decision_id"], decision["decision_id"], "decision_proof.decision_id")
    counts = _object(proof["reference_counts"], "decision_proof.reference_counts", {
        "evidence", "standing", "delegation", "approval", "context",
    })
    for name in ("evidence", "standing", "delegation", "approval", "context"):
        path = "decision_proof." + name + "_refs"
        length = _refs(proof[name + "_refs"], path, summary=summary)
        _count(counts[name], "decision_proof.reference_counts." + name)
        if length is not None and length != counts[name]:
            raise WarrantFormatError(path + " count mismatch")
        if summary:
            if length is not None:
                raise WarrantFormatError(path + " must be omitted")
            omitted_expected.append(path)

    lifecycle = [root[name] for name in (
        "execution_attempt", "adapter_result", "verification", "effect", "effect_proof",
    )]
    if any(item is None for item in lifecycle) and any(item is not None for item in lifecycle):
        raise WarrantFormatError("partial execution path is invalid")
    if all(item is not None for item in lifecycle):
        _validate_assured(root, summary, omitted_expected)
    if omitted != omitted_expected:
        raise WarrantFormatError("disclosure.omitted_fields does not match the profile")


def _parameters(value: object, path: str, summary: bool) -> None:
    if summary and value is None:
        return
    if not isinstance(value, dict):
        raise WarrantFormatError(path + " must be an object")
    if summary:
        raise WarrantFormatError(path + " must be omitted")


def _validate_assured(root: dict[str, object], summary: bool, omitted: list[str]) -> None:
    execution = _object(root["execution_attempt"], "execution_attempt", {
        "execution_attempt_id", "decision_id", "previous_execution_attempt_id",
    })
    adapter = _object(root["adapter_result"], "adapter_result", {
        "result_id", "execution_attempt_id", "state", "origin", "references", "reference_count",
    })
    verification = _object(root["verification"], "verification", {
        "verification_id", "adapter_result_id", "state", "references", "reference_count",
    })
    effect = _object(root["effect"], "effect", {
        "effect_id", "consequence_id", "state", "verification_refs", "verification_ref_count",
    })
    proof = _object(root["effect_proof"], "effect_proof", {
        "proof_id", "effect_id", "verification_id",
    })
    for obj, names, path in (
        (execution, ("execution_attempt_id",), "execution_attempt"),
        (adapter, ("result_id",), "adapter_result"),
        (verification, ("verification_id",), "verification"),
        (effect, ("effect_id",), "effect"),
        (proof, ("proof_id",), "effect_proof"),
    ):
        for name in names:
            _id(obj[name], path + "." + name)
    _id(execution["previous_execution_attempt_id"], "execution_attempt.previous_execution_attempt_id", nullable=True)
    if execution["previous_execution_attempt_id"] == execution["execution_attempt_id"]:
        raise WarrantFormatError("execution_attempt cannot link to itself")
    for value, target, path in (
        (execution["decision_id"], root["decision"]["decision_id"], "execution_attempt.decision_id"),
        (adapter["execution_attempt_id"], execution["execution_attempt_id"], "adapter_result.execution_attempt_id"),
        (verification["adapter_result_id"], adapter["result_id"], "verification.adapter_result_id"),
        (effect["consequence_id"], root["consequence"]["consequence_id"], "effect.consequence_id"),
        (proof["effect_id"], effect["effect_id"], "effect_proof.effect_id"),
        (proof["verification_id"], verification["verification_id"], "effect_proof.verification_id"),
    ):
        _link(value, target, path)
    if adapter["state"] not in ("acknowledged", "rejected", "error", "unknown"):
        raise WarrantFormatError("invalid adapter state")
    if adapter["origin"] not in ("adapter", "sdk_recovery", "unspecified"):
        raise WarrantFormatError("invalid adapter origin")
    states = {
        "verified_bound": "bound", "verified_no_bind": "no_bind",
        "inconclusive": "effect_unknown",
    }
    if verification["state"] not in states or effect["state"] != states[verification["state"]]:
        raise WarrantFormatError("verification and effect states do not agree")
    lengths = []
    for obj, key, count_key, path in (
        (adapter, "references", "reference_count", "adapter_result.references"),
        (verification, "references", "reference_count", "verification.references"),
        (effect, "verification_refs", "verification_ref_count", "effect.verification_refs"),
    ):
        length = _refs(obj[key], path, summary=summary)
        _count(obj[count_key], path + " count")
        if length is not None and length != obj[count_key]:
            raise WarrantFormatError(path + " count mismatch")
        if summary:
            if length is not None:
                raise WarrantFormatError(path + " must be omitted")
            omitted.append(path)
        lengths.append(length)
    if verification["state"] != "inconclusive" and verification["reference_count"] == 0:
        raise WarrantFormatError("conclusive verification requires references")
    if verification["reference_count"] != effect["verification_ref_count"]:
        raise WarrantFormatError("verification and effect reference counts differ")
    if not summary and verification["references"] != effect["verification_refs"]:
        raise WarrantFormatError("verification and effect references differ")
    if adapter["origin"] == "sdk_recovery":
        if adapter["state"] != "unknown":
            raise WarrantFormatError("SDK recovery requires unknown adapter state")
        if not summary and _RECOVERY_MARKER not in adapter["references"]:
            raise WarrantFormatError("SDK recovery marker missing")
    if adapter["origin"] == "adapter" and not summary and _RECOVERY_MARKER in adapter["references"]:
        raise WarrantFormatError("SDK recovery marker cannot be adapter-issued")


def parse_warrant(data: str | bytes) -> PortableWarrant:
    """Parse a bounded portable record into detached inspection data."""
    if not isinstance(data, (str, bytes)):
        raise CAGETypeError("data must be str or bytes")
    try:
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        if len(encoded) > 8 * 1024 * 1024:
            raise WarrantFormatError("portable Warrant exceeds the 8 MiB limit")
        value = json.loads(
            encoded.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=_nonfinite,
        )
        _check_depth(value)
        _validate_decoded(value)
        return PortableWarrant(value)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as error:
        raise WarrantFormatError("invalid UTF-8 JSON Warrant") from error
    except WarrantExportError as error:
        raise WarrantFormatError(str(error)) from error
