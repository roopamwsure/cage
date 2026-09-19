from dataclasses import FrozenInstanceError, fields

import pytest

from cage.errors import CAGETypeError, CAGEValueError
from cage.identifiers import AssuranceIds, EvaluationIds


def test_evaluation_ids_have_the_documented_fields() -> None:
    assert [field.name for field in fields(EvaluationIds)] == [
        "consequence_id",
        "attempt_id",
        "decision_id",
        "decision_proof_id",
        "warrant_id",
    ]


def test_assurance_ids_have_the_documented_fields() -> None:
    assert [field.name for field in fields(AssuranceIds)] == [
        "effect_id",
        "effect_proof_id",
        "warrant_id",
    ]


def test_identifier_overrides_default_to_none() -> None:
    assert EvaluationIds() == EvaluationIds(
        consequence_id=None,
        attempt_id=None,
        decision_id=None,
        decision_proof_id=None,
        warrant_id=None,
    )
    assert AssuranceIds() == AssuranceIds(
        effect_id=None,
        effect_proof_id=None,
        warrant_id=None,
    )


def test_identifier_overrides_preserve_explicit_values() -> None:
    evaluation_ids = EvaluationIds(
        consequence_id="consequence-explicit",
        attempt_id="attempt-explicit",
        decision_id="decision-explicit",
        decision_proof_id="decision-proof-explicit",
        warrant_id="warrant-evaluation",
    )
    assurance_ids = AssuranceIds(
        effect_id="effect-explicit",
        effect_proof_id="effect-proof-explicit",
        warrant_id="warrant-assurance",
    )

    assert evaluation_ids.consequence_id == "consequence-explicit"
    assert evaluation_ids.attempt_id == "attempt-explicit"
    assert evaluation_ids.decision_id == "decision-explicit"
    assert evaluation_ids.decision_proof_id == "decision-proof-explicit"
    assert evaluation_ids.warrant_id == "warrant-evaluation"
    assert assurance_ids.effect_id == "effect-explicit"
    assert assurance_ids.effect_proof_id == "effect-proof-explicit"
    assert assurance_ids.warrant_id == "warrant-assurance"


@pytest.mark.parametrize(
    ("override_type", "field_name"),
    [
        (EvaluationIds, "consequence_id"),
        (EvaluationIds, "attempt_id"),
        (EvaluationIds, "decision_id"),
        (EvaluationIds, "decision_proof_id"),
        (EvaluationIds, "warrant_id"),
        (AssuranceIds, "effect_id"),
        (AssuranceIds, "effect_proof_id"),
        (AssuranceIds, "warrant_id"),
    ],
)
def test_identifier_overrides_reject_non_string_values(
    override_type: type[EvaluationIds] | type[AssuranceIds],
    field_name: str,
) -> None:
    with pytest.raises(CAGETypeError, match=rf"{field_name} must be a string or None"):
        override_type(**{field_name: 42})


@pytest.mark.parametrize(
    ("override_type", "field_name"),
    [
        (EvaluationIds, "consequence_id"),
        (EvaluationIds, "attempt_id"),
        (EvaluationIds, "decision_id"),
        (EvaluationIds, "decision_proof_id"),
        (EvaluationIds, "warrant_id"),
        (AssuranceIds, "effect_id"),
        (AssuranceIds, "effect_proof_id"),
        (AssuranceIds, "warrant_id"),
    ],
)
def test_identifier_overrides_reject_blank_values(
    override_type: type[EvaluationIds] | type[AssuranceIds],
    field_name: str,
) -> None:
    with pytest.raises(CAGEValueError, match=rf"{field_name} must not be blank"):
        override_type(**{field_name: "   "})


def test_identifier_overrides_are_immutable() -> None:
    evaluation_ids = EvaluationIds()
    assurance_ids = AssuranceIds()

    with pytest.raises(FrozenInstanceError):
        evaluation_ids.attempt_id = "changed"

    with pytest.raises(FrozenInstanceError):
        assurance_ids.effect_id = "changed"