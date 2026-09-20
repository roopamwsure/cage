def test_rules_exports_existing_core_contracts() -> None:
    from cage.core.action import RequestedEffect as CoreRequestedEffect
    from cage.core.assurance import (
        Approval as CoreApproval,
        Context as CoreContext,
        Delegation as CoreDelegation,
        Evidence as CoreEvidence,
        Standing as CoreStanding,
    )
    from cage.core.attempt import Attempt as CoreAttempt
    from cage.core.decision import DecisionState as CoreDecisionState
    from cage.core.evaluation import (
        EvaluationOutcome as CoreEvaluationOutcome,
        EvaluationRule as CoreEvaluationRule,
    )
    from cage.rules import (
        Approval,
        Attempt,
        Context,
        DecisionState,
        Delegation,
        Evidence,
        EvaluationOutcome,
        EvaluationRule,
        RequestedEffect,
        Standing,
    )

    assert RequestedEffect is CoreRequestedEffect
    assert Approval is CoreApproval
    assert Context is CoreContext
    assert Delegation is CoreDelegation
    assert Evidence is CoreEvidence
    assert Standing is CoreStanding
    assert Attempt is CoreAttempt
    assert DecisionState is CoreDecisionState
    assert EvaluationOutcome is CoreEvaluationOutcome
    assert EvaluationRule is CoreEvaluationRule


def test_adapters_exports_existing_core_contracts() -> None:
    from cage.adapters import (
        AdapterExecutionResult,
        AdapterExecutionState,
        EffectAdapter,
        ExecutionAttempt,
        ExecutionCapability,
        RequestedEffect,
    )
    from cage.core.action import RequestedEffect as CoreRequestedEffect
    from cage.core.adapter import (
        AdapterExecutionResult as CoreAdapterExecutionResult,
        AdapterExecutionState as CoreAdapterExecutionState,
        EffectAdapter as CoreEffectAdapter,
    )
    from cage.core.capability import (
        ExecutionCapability as CoreExecutionCapability,
    )
    from cage.core.execution import ExecutionAttempt as CoreExecutionAttempt

    assert AdapterExecutionResult is CoreAdapterExecutionResult
    assert AdapterExecutionState is CoreAdapterExecutionState
    assert EffectAdapter is CoreEffectAdapter
    assert ExecutionAttempt is CoreExecutionAttempt
    assert ExecutionCapability is CoreExecutionCapability
    assert RequestedEffect is CoreRequestedEffect


def test_verifiers_exports_existing_core_contracts() -> None:
    from cage.core.adapter import (
        AdapterExecutionResult as CoreAdapterExecutionResult,
    )
    from cage.core.verification import (
        EffectVerificationResult as CoreEffectVerificationResult,
        EffectVerifier as CoreEffectVerifier,
        VerificationState as CoreVerificationState,
    )
    from cage.verifiers import (
        AdapterExecutionResult,
        EffectVerificationResult,
        EffectVerifier,
        VerificationState,
    )

    assert AdapterExecutionResult is CoreAdapterExecutionResult
    assert EffectVerificationResult is CoreEffectVerificationResult
    assert EffectVerifier is CoreEffectVerifier
    assert VerificationState is CoreVerificationState


def test_results_exports_existing_core_contracts() -> None:
    from cage.core.decision import (
        Decision as CoreDecision,
        DecisionState as CoreDecisionState,
    )
    from cage.core.effect import (
        Effect as CoreEffect,
        EffectState as CoreEffectState,
    )
    from cage.results import (
        AssuranceResult,
        Decision,
        DecisionState,
        Effect,
        EffectState,
        EvaluationResult,
        ExecutionObservationOrigin,
        ExecutionResult,
    )

    assert Decision is CoreDecision
    assert DecisionState is CoreDecisionState
    assert Effect is CoreEffect
    assert EffectState is CoreEffectState
    assert EvaluationResult.__module__ == "cage.results"
    assert ExecutionResult.__module__ == "cage.results"
    assert AssuranceResult.__module__ == "cage.results"
    assert ExecutionObservationOrigin.__module__ == "cage.results"