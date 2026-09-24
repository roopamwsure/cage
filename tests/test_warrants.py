from dataclasses import replace

import pytest

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability
from cage.core.adapter import AdapterExecutionResult, AdapterExecutionState
from cage.core.verification import EffectVerificationResult, VerificationState
from cage.core.warrant import Warrant
from cage.errors import CAGETypeError, WarrantExportError
from cage.warrants import WarrantDisclosure, export_warrant


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

    assert document.observation_origin == "unspecified"
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
