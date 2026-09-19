from dataclasses import dataclass

from cage.errors import CAGETypeError
from cage.identifiers import IdFactory, uuid_id


@dataclass(frozen=True, slots=True)
class CAGEConfig:
    """Immutable configuration for the CAGE developer SDK."""

    id_factory: IdFactory = uuid_id

    def __post_init__(self) -> None:
        if not callable(self.id_factory):
            raise CAGETypeError("id_factory must be callable")