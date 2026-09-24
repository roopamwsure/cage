import pytest

from cage import CAGE, DecisionState, EvaluationOutcome
from cage.errors import CAGETypeError, WarrantExportError
from cage.warrants import WarrantDisclosure, export_warrant


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
