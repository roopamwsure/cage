import pytest

from cage._facade import CAGE
from cage.config import CAGEConfig
from cage.core.decision import DecisionState
from cage.core.evaluation import EvaluationOutcome
from cage.errors import CAGETypeError
from cage.identifiers import IdentityKind
from cage.inputs import CAGEInputs


def _admit_rule(*args: object) -> EvaluationOutcome:
    return EvaluationOutcome(state=DecisionState.ADMITTED)


def test_facade_uses_default_configuration() -> None:
    cage = CAGE(rule=_admit_rule)

    assert type(cage.config) is CAGEConfig
    assert type(cage.inputs) is CAGEInputs


def test_facade_preserves_explicit_configuration() -> None:
    generated_kinds: list[IdentityKind] = []

    def deterministic_id(kind: IdentityKind) -> str:
        generated_kinds.append(kind)
        return f"generated_{kind.value}"

    config = CAGEConfig(id_factory=deterministic_id)
    cage = CAGE(rule=_admit_rule, config=config)

    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )

    assert cage.config is config
    assert action.action_id == "generated_action"
    assert generated_kinds == [IdentityKind.ACTION]


@pytest.mark.parametrize("invalid_rule", [None, "rule", 42, object()])
def test_facade_rejects_noncallable_rule(invalid_rule: object) -> None:
    with pytest.raises(CAGETypeError, match="rule must be callable"):
        CAGE(rule=invalid_rule)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_config", ["config", 42, object()])
def test_facade_rejects_invalid_configuration(
    invalid_config: object,
) -> None:
    with pytest.raises(
        CAGETypeError,
        match="config must be a CAGEConfig or None",
    ):
        CAGE(  # type: ignore[arg-type]
            rule=_admit_rule,
            config=invalid_config,
        )


def test_facade_properties_are_read_only() -> None:
    cage = CAGE(rule=_admit_rule)

    with pytest.raises(AttributeError):
        cage.config = CAGEConfig()

    with pytest.raises(AttributeError):
        cage.inputs = CAGEInputs(
            id_factory=lambda kind: f"other_{kind.value}"
        )


def test_facade_is_not_exported_from_package_root_yet() -> None:
    import cage

    assert not hasattr(cage, "CAGE")