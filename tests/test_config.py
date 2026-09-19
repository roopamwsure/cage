from dataclasses import FrozenInstanceError

import pytest

from cage.config import CAGEConfig
from cage.errors import CAGETypeError
from cage.identifiers import IdentityKind, uuid_id


def test_config_defaults_to_uuid_id() -> None:
    config = CAGEConfig()

    assert config.id_factory is uuid_id


def test_config_preserves_custom_id_factory() -> None:
    def deterministic_id(kind: IdentityKind) -> str:
        return f"test_{kind.value}"

    config = CAGEConfig(id_factory=deterministic_id)

    assert config.id_factory is deterministic_id
    assert config.id_factory(IdentityKind.ACTION) == "test_action"


@pytest.mark.parametrize("invalid_factory", [None, "uuid_id", 42, object()])
def test_config_rejects_noncallable_id_factory(invalid_factory: object) -> None:
    with pytest.raises(CAGETypeError, match="id_factory must be callable"):
        CAGEConfig(id_factory=invalid_factory)  # type: ignore[arg-type]


def test_config_is_immutable() -> None:
    config = CAGEConfig()

    with pytest.raises(FrozenInstanceError):
        config.id_factory = lambda kind: kind.value