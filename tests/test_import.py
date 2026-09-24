def test_package_imports() -> None:
    import cage

    assert cage is not None


def test_cage_config_is_exported_from_package_root() -> None:
    from cage import CAGEConfig
    from cage.config import CAGEConfig as ConfigModuleCAGEConfig

    assert CAGEConfig is ConfigModuleCAGEConfig


def test_functional_cage_facade_is_exported_from_package_root() -> None:
    from cage import CAGE
    from cage._facade import CAGE as FacadeCAGE

    assert CAGE is FacadeCAGE


def test_core_developer_types_are_exported_from_package_root() -> None:
    import cage
    from cage.core.action import Action, RequestedEffect
    from cage.core.assurance import (
        Approval,
        Context,
        Delegation,
        Evidence,
        Standing,
    )
    from cage.core.capability import ExecutionCapability
    from cage.core.decision import DecisionState
    from cage.core.effect import EffectState
    from cage.core.evaluation import EvaluationOutcome
    from cage.core.identity import Agent, Principal, Resource

    expected = {
        "Action": Action,
        "RequestedEffect": RequestedEffect,
        "Principal": Principal,
        "Agent": Agent,
        "Resource": Resource,
        "Evidence": Evidence,
        "Standing": Standing,
        "Delegation": Delegation,
        "Approval": Approval,
        "Context": Context,
        "EvaluationOutcome": EvaluationOutcome,
        "DecisionState": DecisionState,
        "EffectState": EffectState,
        "ExecutionCapability": ExecutionCapability,
    }
    for name, canonical_type in expected.items():
        assert getattr(cage, name) is canonical_type
        assert name in cage.__all__


def test_sdk_identifier_result_and_error_imports() -> None:
    from cage.errors import (
        AdapterContractError,
        AdapterInvocationError,
        AdapterResultMismatchError,
        AssuranceAssemblyError,
        CAGEError,
        CAGETypeError,
        CAGEValueError,
        DuplicateExecutionError,
        DuplicateReconciliationError,
        DuplicateVerificationError,
        ExecutionError,
        IdentifierGenerationError,
        VerificationResultMismatchError,
        VerifierContractError,
        VerifierInvocationError,
    )
    from cage.identifiers import (
        AssuranceIds,
        EvaluationIds,
        IdFactory,
        IdentityKind,
        uuid_id,
    )
    from cage.results import (
        AssuranceResult,
        EvaluationResult,
        ExecutionObservationOrigin,
        ExecutionResult,
    )

    assert AssuranceIds().effect_id is None
    assert EvaluationIds().consequence_id is None
    assert IdentityKind.WARRANT.value == "warrant"
    assert callable(uuid_id)
    assert IdFactory is not None
    assert all(
        isinstance(result_type, type)
        for result_type in (EvaluationResult, ExecutionResult, AssuranceResult)
    )
    assert ExecutionObservationOrigin.SDK_RECOVERY.value == "sdk_recovery"
    assert all(
        issubclass(error_type, CAGEError)
        for error_type in (
            CAGETypeError,
            CAGEValueError,
            IdentifierGenerationError,
            ExecutionError,
            AdapterInvocationError,
            AdapterContractError,
            AdapterResultMismatchError,
            VerifierInvocationError,
            VerifierContractError,
            VerificationResultMismatchError,
            AssuranceAssemblyError,
            DuplicateExecutionError,
            DuplicateReconciliationError,
            DuplicateVerificationError,
        )
    )


def test_portable_warrant_public_imports_are_stable() -> None:
    import cage.warrants as portable
    from cage.core.warrant import DecisionProof, EffectProof, Warrant
    from cage.errors import (
        WarrantExportError, WarrantFormatError, WarrantIOError,
        UnsupportedWarrantVersionError,
    )

    assert portable.Warrant is Warrant
    assert portable.DecisionProof is DecisionProof
    assert portable.EffectProof is EffectProof
    assert set(portable.__all__) == {
        "Warrant", "DecisionProof", "EffectProof", "PortableWarrant",
        "WarrantDisclosure", "ValidationIssue", "WarrantValidationReport",
        "export_warrant", "parse_warrant", "load_warrant", "dump_warrant",
        "validate_warrant",
    }
    assert all(callable(getattr(portable, name)) for name in (
        "export_warrant", "parse_warrant", "load_warrant", "dump_warrant",
        "validate_warrant",
    ))
    assert issubclass(UnsupportedWarrantVersionError, WarrantFormatError)
    assert issubclass(WarrantExportError, ValueError)
    assert issubclass(WarrantIOError, OSError)
