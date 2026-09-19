import re

import pytest

from cage.errors import CAGETypeError
from cage.identifiers import IdentityKind, IdFactory, uuid_id


def test_identity_kind_has_the_documented_namespaces() -> None:
    assert {kind.name: kind.value for kind in IdentityKind} == {
        "ACTION": "action",
        "CONSEQUENCE": "consequence",
        "ATTEMPT": "attempt",
        "DECISION": "decision",
        "DECISION_PROOF": "decision_proof",
        "EXECUTION_ATTEMPT": "execution_attempt",
        "ADAPTER_RESULT": "adapter_result",
        "VERIFICATION": "verification",
        "EFFECT": "effect",
        "EFFECT_PROOF": "effect_proof",
        "WARRANT": "warrant",
        "EVIDENCE": "evidence",
        "STANDING": "standing",
        "DELEGATION": "delegation",
        "APPROVAL": "approval",
        "CONTEXT": "context",
    }


def test_identity_kind_is_a_string_enum() -> None:
    assert isinstance(IdentityKind.ACTION, str)
    assert IdentityKind.ACTION == "action"


@pytest.mark.parametrize("kind", list(IdentityKind))
def test_uuid_id_uses_kind_prefix_and_uuid4_hex(kind: IdentityKind) -> None:
    generated = uuid_id(kind)

    assert re.fullmatch(rf"{re.escape(kind.value)}_[0-9a-f]{{32}}", generated)


def test_uuid_id_generates_distinct_identifiers() -> None:
    assert uuid_id(IdentityKind.ACTION) != uuid_id(IdentityKind.ACTION)


def test_uuid_id_satisfies_id_factory_contract() -> None:
    factory: IdFactory = uuid_id

    assert factory(IdentityKind.WARRANT).startswith("warrant_")


@pytest.mark.parametrize("invalid_kind", ["action", None, 1])
def test_uuid_id_rejects_non_identity_kinds(invalid_kind: object) -> None:
    with pytest.raises(CAGETypeError, match="kind must be an IdentityKind"):
        uuid_id(invalid_kind)  # type: ignore[arg-type]