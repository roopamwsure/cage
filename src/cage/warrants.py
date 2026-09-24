"""Detached, inspection-only projections of native Warrants."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import json

from cage.core._json import freeze_json_value
from cage.core.decision import DecisionState
from cage.core.effect import EffectState
from cage.core.warrant import Warrant
from cage.errors import CAGETypeError, CAGEValueError, WarrantExportError
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
