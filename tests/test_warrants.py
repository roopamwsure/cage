from dataclasses import replace
import json
from pathlib import Path

import pytest

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability
from cage.core.adapter import AdapterExecutionResult, AdapterExecutionState
from cage.core.verification import EffectVerificationResult, VerificationState
from cage.core.warrant import Warrant
from cage.errors import (
    CAGETypeError, UnsupportedWarrantVersionError,
    WarrantExportError, WarrantFormatError, WarrantIOError,
)
from cage.warrants import (
    WarrantDisclosure, dump_warrant, export_warrant, load_warrant,
    parse_warrant, validate_warrant,
)


def _assurance(*, state=VerificationState.VERIFIED_BOUND):
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="private-principal",
        agent_id="private-agent", resource_id="private-resource",
        requested_effect={"secret": "private-value"},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="private-key")

    class Adapter:
        def execute(self, *, execution_attempt, effect, capability):
            return AdapterExecutionResult(
                result_id="result-1", execution_attempt=execution_attempt,
                state=AdapterExecutionState.ACKNOWLEDGED,
                references=("private-receipt",),
            )

    class Verifier:
        def verify(self, *, adapter_result):
            return EffectVerificationResult(
                verification_id="verification-1", adapter_result=adapter_result,
                state=state, references=("private-proof", "private-proof")
                if state is VerificationState.VERIFIED_BOUND else (),
            )

    execution = cage.execute(
        evaluation, adapter=Adapter(),
        capability=ExecutionCapability(
            capability_id="capability-1", consequence_id=evaluation.consequence_id,
            action_type="database.delete", resource_id="private-resource",
        ),
    )
    return cage.verify(execution, verifier=Verifier())


def test_assured_summary_preserves_links_and_counts_without_private_references() -> None:
    assurance = _assurance()
    document = export_warrant(assurance)
    payload = document.to_dict()

    assert document.execution_attempt_id == assurance.execution_attempt.execution_attempt_id
    assert document.effect_state == assurance.effect.state
    assert document.observation_origin == "adapter"
    assert payload["adapter_result"]["origin"] == "adapter"
    assert payload["adapter_result"]["references"] is None
    assert payload["adapter_result"]["reference_count"] == 1
    assert payload["verification"]["references"] is None
    assert payload["verification"]["reference_count"] == 2
    assert payload["effect"]["verification_refs"] is None
    assert payload["effect"]["verification_ref_count"] == 2
    assert payload["effect_proof"]["verification_id"] == "verification-1"
    assert payload["effect_proof"]["effect_id"] == assurance.effect.effect_id
    assert payload["decision"]["decision_id"] == payload["execution_attempt"]["decision_id"]
    assert payload["warrant"]["previous_warrant_id"] == assurance.execution.evaluation.warrant.warrant_id
    assert "private" not in document.to_json()
    assert payload["disclosure"]["omitted_fields"][-3:] == [
        "adapter_result.references", "verification.references", "effect.verification_refs",
    ]


def test_assured_full_preserves_ordered_duplicate_references_and_core_origin() -> None:
    assurance = _assurance()
    document = export_warrant(assurance.warrant, disclosure=WarrantDisclosure.FULL)
    payload = document.to_dict()

    assert document.observation_origin is None
    assert payload["adapter_result"]["origin"] == "unspecified"
    assert payload["adapter_result"]["references"] == ["private-receipt"]
    assert payload["verification"]["references"] == ["private-proof", "private-proof"]
    assert payload["effect"]["verification_refs"] == ["private-proof", "private-proof"]
    assert payload["disclosure"]["omitted_fields"] == []


def test_inconclusive_assurance_keeps_effect_unknown_and_lineage() -> None:
    assurance = _assurance(state=VerificationState.INCONCLUSIVE)
    document = export_warrant(assurance)
    payload = document.to_dict()
    assert document.effect_state.value == "effect_unknown"
    assert payload["verification"]["state"] == "inconclusive"
    assert payload["verification"]["reference_count"] == 0
    assert payload["effect"]["verification_ref_count"] == 0
    assert document.previous_warrant_id == assurance.execution.evaluation.warrant.warrant_id


def test_core_recovery_marker_records_origin_even_when_summary_hides_references() -> None:
    assurance = _assurance(state=VerificationState.INCONCLUSIVE)
    original = assurance.adapter_result
    recovery = replace(
        original, state=AdapterExecutionState.UNKNOWN,
        references=("urn:cage:sdk:recovery-observation",),
    )
    verification = replace(assurance.verification, adapter_result=recovery)
    effect_proof = replace(assurance.effect_proof, verification=verification)
    warrant = replace(assurance.warrant, effect_proof=effect_proof)
    document = export_warrant(warrant)
    assert document.observation_origin == "sdk_recovery"
    assert document.to_dict()["adapter_result"]["references"] is None
    assert export_warrant(warrant, disclosure=WarrantDisclosure.FULL).to_dict()[
        "adapter_result"
    ]["references"] == ["urn:cage:sdk:recovery-observation"]


def test_assured_export_rejects_cross_decision_path_in_raw_warrant() -> None:
    first = _assurance()
    inconsistent = Warrant(
        warrant_id="inconsistent", schema_version="0.7",
        decision_proof=replace(
            first.decision_proof,
            decision=replace(first.decision, decision_id="other-decision"),
        ),
        effect_proof=first.effect_proof,
    )
    with pytest.raises(WarrantExportError, match="decision"):
        export_warrant(inconsistent)


@pytest.mark.parametrize("disclosure", list(WarrantDisclosure))
def test_parse_roundtrip_preserves_detached_assurance(disclosure) -> None:
    original = export_warrant(_assurance(), disclosure=disclosure)
    parsed = parse_warrant(original.to_json().encode("utf-8"))
    assert parsed.to_dict() == original.to_dict()
    assert parsed.warrant_id == original.warrant_id
    assert parsed.observation_origin == "adapter"
    parsed_dict = parsed.to_dict()
    parsed_dict["warrant"]["warrant_id"] = "changed"
    assert parsed.warrant_id == original.warrant_id


def test_parse_decision_only_record_has_no_effect_or_execution() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="p", agent_id="a",
        resource_id="r", requested_effect={"id": 1},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="key")
    original = export_warrant(evaluation)
    parsed = parse_warrant(original.to_json())
    assert parsed.to_dict() == original.to_dict()
    assert parsed.effect_state is None
    assert parsed.observation_origin is None


def test_parse_rejects_duplicate_keys_and_nonfinite_numbers() -> None:
    document = export_warrant(_assurance()).to_dict()
    encoded = json.dumps(document)
    with pytest.raises(WarrantFormatError, match="duplicate"):
        parse_warrant(encoded.replace('"format": "cage.warrant",',
                                      '"format": "cage.warrant", "format": "cage.warrant",', 1))
    with pytest.raises(WarrantFormatError, match="nonfinite"):
        parse_warrant(encoded.replace('"reference_count": 1', '"reference_count": NaN', 1))


def test_parse_rejects_unsupported_version_and_unknown_fields() -> None:
    payload = export_warrant(_assurance()).to_dict()
    payload["format_version"] = "2"
    with pytest.raises(UnsupportedWarrantVersionError):
        parse_warrant(json.dumps(payload))
    payload["format_version"] = "1"
    payload["action"]["unexpected"] = "secret"
    with pytest.raises(WarrantFormatError, match="unknown"):
        parse_warrant(json.dumps(payload))


def test_parse_rejects_wrong_links_and_undisclosed_omission() -> None:
    payload = export_warrant(_assurance()).to_dict()
    payload["execution_attempt"]["decision_id"] = "different"
    with pytest.raises(WarrantFormatError, match="decision_id"):
        parse_warrant(json.dumps(payload))
    payload = export_warrant(_assurance()).to_dict()
    payload["disclosure"]["omitted_fields"] = []
    with pytest.raises(WarrantFormatError, match="omitted_fields"):
        parse_warrant(json.dumps(payload))


def test_parse_rejects_invalid_utf8_and_oversized_input() -> None:
    with pytest.raises(WarrantFormatError, match="UTF-8"):
        parse_warrant(b"\xff")
    with pytest.raises(WarrantFormatError, match="8 MiB"):
        parse_warrant(b" " * (8 * 1024 * 1024 + 1))
    with pytest.raises(CAGETypeError):
        parse_warrant({})


def test_parse_rejects_conflicting_effect_states_and_reference_counts() -> None:
    payload = export_warrant(_assurance(), disclosure=WarrantDisclosure.FULL).to_dict()
    payload["effect"]["state"] = "no_bind"
    with pytest.raises(WarrantFormatError, match="states"):
        parse_warrant(json.dumps(payload))
    payload = export_warrant(_assurance(), disclosure=WarrantDisclosure.FULL).to_dict()
    payload["verification"]["reference_count"] = 3
    with pytest.raises(WarrantFormatError, match="count"):
        parse_warrant(json.dumps(payload))
    payload = export_warrant(_assurance()).to_dict()
    payload["decision_proof"]["reference_counts"]["evidence"] = True
    with pytest.raises(WarrantFormatError, match="nonnegative integer"):
        parse_warrant(json.dumps(payload))


def test_parse_rejects_deep_record_and_nonfinite_overflow() -> None:
    payload = export_warrant(_assurance(), disclosure=WarrantDisclosure.FULL).to_dict()
    nested: object = "value"
    for _ in range(65):
        nested = [nested]
    payload["action"]["requested_effect"]["parameters"] = {"nested": nested}
    with pytest.raises(WarrantFormatError, match="depth"):
        parse_warrant(json.dumps(payload))
    encoded = export_warrant(_assurance(), disclosure=WarrantDisclosure.FULL).to_json()
    with pytest.raises(WarrantFormatError):
        parse_warrant(encoded.replace('"reference_count": 1', '"reference_count": 1e999', 1))


def test_validation_reports_structural_failure_without_raising() -> None:
    payload = export_warrant(_assurance()).to_dict()
    payload["effect"]["state"] = "no_bind"
    report = validate_warrant(json.dumps(payload))
    assert report.structurally_valid is False
    assert report.disclosure is WarrantDisclosure.SUMMARY
    assert report.issues == (
        report.issues[0],
    )
    assert report.issues[0].severity == "error"
    assert report.issues[0].code == "invalid_format"
    assert report.issues[0].path == "effect.state"
    assert "states" in report.issues[0].message


def test_validation_identifies_unsupported_format_without_disclosure() -> None:
    payload = export_warrant(_assurance()).to_dict()
    payload["format_version"] = "2"
    report = validate_warrant(json.dumps(payload))
    assert report.structurally_valid is False
    assert report.disclosure is None
    assert report.issues[0].code == "unsupported_version"
    assert report.issues[0].path == "format_version"


def test_valid_summary_reports_hidden_references_and_unresolved_predecessor() -> None:
    document = export_warrant(_assurance())
    report = validate_warrant(document)
    assert report.structurally_valid is True
    assert report.disclosure is WarrantDisclosure.SUMMARY
    assert all(issue.severity == "warning" for issue in report.issues)
    assert {issue.code for issue in report.issues} >= {
        "hidden_references", "unresolved_predecessor",
    }
    assert any(issue.path == "warrant.previous_warrant_id" for issue in report.issues)


def test_full_decision_only_warrant_has_no_hidden_reference_warning() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="p", agent_id="a",
        resource_id="r", requested_effect={},
    )
    document = export_warrant(cage.evaluate(action=action, idempotency_key="k"),
                              disclosure=WarrantDisclosure.FULL)
    report = validate_warrant(document.to_json())
    assert report.structurally_valid is True
    assert report.disclosure is WarrantDisclosure.FULL
    assert report.issues == ()


def test_validation_rejects_only_invalid_api_argument_type() -> None:
    with pytest.raises(CAGETypeError):
        validate_warrant(123)
    report = validate_warrant(b"\xff")
    assert report.structurally_valid is False
    assert report.disclosure is None


def test_validation_warns_for_recorded_execution_after_held_decision() -> None:
    assurance = _assurance()
    held = replace(assurance.decision, state=DecisionState.HELD)
    execution_attempt = replace(assurance.execution_attempt, decision=held)
    adapter = replace(assurance.adapter_result, execution_attempt=execution_attempt)
    verification = replace(assurance.verification, adapter_result=adapter)
    proof = replace(assurance.effect_proof, verification=verification)
    warrant = replace(
        assurance.warrant,
        decision_proof=replace(assurance.decision_proof, decision=held),
        effect_proof=proof,
    )
    report = validate_warrant(export_warrant(warrant))
    assert report.structurally_valid is True
    assert any(issue.code == "ineligible_execution" and issue.path == "decision.state"
               for issue in report.issues)


def test_dump_load_utf8_roundtrip_outside_current_directory(tmp_path: Path) -> None:
    document = export_warrant(_assurance(), disclosure=WarrantDisclosure.FULL)
    destination = tmp_path / "warrant-秘密.json"
    dump_warrant(document, destination)
    assert destination.read_bytes() == document.to_json().encode("utf-8")
    assert load_warrant(destination).to_dict() == document.to_dict()


def test_dump_refuses_existing_file_without_overwriting(tmp_path: Path) -> None:
    document = export_warrant(_assurance())
    destination = tmp_path / "existing.json"
    destination.write_text("original", encoding="utf-8")
    with pytest.raises(WarrantIOError, match="exists"):
        dump_warrant(document, destination)
    assert destination.read_text(encoding="utf-8") == "original"
    dump_warrant(document, destination, overwrite=True)
    assert load_warrant(destination).to_dict() == document.to_dict()


def test_dump_validates_before_replacing_existing_destination(tmp_path: Path) -> None:
    from cage.warrants import PortableWarrant

    destination = tmp_path / "existing.json"
    destination.write_text("original", encoding="utf-8")
    invalid = PortableWarrant({"format": "cage.warrant"})
    with pytest.raises(WarrantFormatError):
        dump_warrant(invalid, destination, overwrite=True)
    assert destination.read_text(encoding="utf-8") == "original"


def test_file_errors_are_wrapped_and_missing_parent_is_not_created(tmp_path: Path) -> None:
    document = export_warrant(_assurance())
    destination = tmp_path / "missing-parent" / "warrant.json"
    with pytest.raises(WarrantIOError):
        dump_warrant(document, destination)
    assert not destination.parent.exists()
    with pytest.raises(WarrantIOError):
        load_warrant(destination)


def test_load_preserves_format_errors_and_rejects_invalid_api_types(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_bytes(b"\xff")
    with pytest.raises(WarrantFormatError):
        load_warrant(malformed)
    with pytest.raises(CAGETypeError):
        load_warrant(123)
    with pytest.raises(CAGETypeError):
        dump_warrant("not-a-document", malformed)
    with pytest.raises(CAGETypeError):
        dump_warrant(export_warrant(_assurance()), malformed, overwrite="yes")
    with pytest.raises(WarrantIOError):
        load_warrant("bad\x00path")
    with pytest.raises(WarrantIOError):
        dump_warrant(export_warrant(_assurance()), "bad\x00path")


def test_decision_only_summary_discloses_omissions_without_leaking_inputs() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="private-principal",
        agent_id="private-agent",
        resource_id="private-resource",
        requested_effect={"secret": ["private-value"]},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="private-key")
    document = export_warrant(evaluation)
    payload = document.to_dict()

    assert document.disclosure is WarrantDisclosure.SUMMARY
    assert document.warrant_id == evaluation.warrant.warrant_id
    assert document.decision_state is DecisionState.ADMITTED
    assert document.effect_state is None
    assert payload["consequence"]["idempotency_key"] is None
    assert payload["action"]["principal_id"] is None
    assert payload["action"]["agent_id"] is None
    assert payload["action"]["resource_id"] is None
    assert payload["action"]["requested_effect"] == {"parameters": None}
    assert payload["decision_proof"]["reference_counts"] == {
        "evidence": 0, "standing": 0, "delegation": 0,
        "approval": 0, "context": 0,
    }
    assert payload["effect_proof"] is None
    assert payload["execution_attempt"] is None
    assert payload["adapter_result"] is None
    assert payload["verification"] is None
    assert payload["effect"] is None
    assert len(payload["disclosure"]["omitted_fields"]) == 10
    assert "private" not in document.to_json()
    payload["action"]["action_type"] = "altered"
    assert document.to_dict()["action"]["action_type"] == "database.delete"


def test_decision_only_full_preserves_inputs_and_reference_counts() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="principal-1",
        agent_id="agent-1", resource_id="resource-1",
        requested_effect={"nested": [1, {"value": True}]},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="key-1")
    payload = export_warrant(evaluation.warrant, disclosure=WarrantDisclosure.FULL).to_dict()

    assert payload["disclosure"] == {"profile": "full", "omitted_fields": []}
    assert payload["action"]["requested_effect"]["parameters"] == {
        "nested": [1, {"value": True}]
    }
    assert payload["consequence"]["idempotency_key"] == "key-1"
    assert payload["action"]["principal_id"] == "principal-1"
    assert payload["decision_proof"]["evidence_refs"] == []


def test_export_rejects_invalid_disclosure_type() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    action = cage.inputs.action(
        action_type="database.delete", principal_id="p", agent_id="a",
        resource_id="r", requested_effect={},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="key")
    with pytest.raises(CAGETypeError, match="disclosure"):
        export_warrant(evaluation, disclosure="invalid")


def test_full_export_rejects_data_deeper_than_format_limit() -> None:
    cage = CAGE(rule=lambda *args: EvaluationOutcome(state=DecisionState.ADMITTED))
    nested: object = "bottom"
    for _ in range(65):
        nested = [nested]
    action = cage.inputs.action(
        action_type="database.delete", principal_id="p", agent_id="a",
        resource_id="r", requested_effect={"nested": nested},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="key")
    with pytest.raises(WarrantExportError, match="depth"):
        export_warrant(evaluation, disclosure=WarrantDisclosure.FULL)
