from cage.core.action import RequestedEffect
from cage.core.adapter import (
    AdapterExecutionResult,
    EffectAdapter,
)
from cage.core.capability import ExecutionCapability
from cage.core.decision import Decision, DecisionState
from cage.core.execution import ExecutionAttempt


class CustodyIneligibleError(ValueError):
    """Raised when a Decision is not eligible for execution custody."""


class CapabilityMismatchError(ValueError):
    """Raised when an execution capability does not match custody intent."""


class AdapterResultMismatchError(ValueError):
    """Raised when an adapter result refers to a different execution attempt."""


def select_effect_for_custody(
    decision: Decision,
) -> RequestedEffect:
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")

    if decision.state is DecisionState.ADMITTED:
        return (
            decision
            .attempt
            .consequence
            .action
            .requested_effect
        )

    if decision.state is DecisionState.NARROWED:
        if decision.permitted_effect is None:
            raise ValueError(
                "NARROWED decision requires a permitted_effect"
            )

        return decision.permitted_effect

    raise CustodyIneligibleError(
        f"{decision.state.value} decision is not eligible for custody"
    )


def validate_capability_for_custody(
    *,
    decision: Decision,
    capability: ExecutionCapability,
) -> None:
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")

    if not isinstance(capability, ExecutionCapability):
        raise TypeError(
            "capability must be an ExecutionCapability"
        )

    consequence = decision.attempt.consequence
    action = consequence.action

    if capability.consequence_id != consequence.consequence_id:
        raise CapabilityMismatchError(
            "capability consequence_id does not match "
            "decision consequence"
        )

    if capability.action_type != action.action_type:
        raise CapabilityMismatchError(
            "capability action_type does not match "
            "decision action"
        )

    if capability.resource_id != action.resource.resource_id:
        raise CapabilityMismatchError(
            "capability resource_id does not match "
            "decision resource"
        )


def execute_under_custody(
    *,
    execution_attempt: ExecutionAttempt,
    capability: ExecutionCapability,
    adapter: EffectAdapter,
) -> AdapterExecutionResult:
    if not isinstance(execution_attempt, ExecutionAttempt):
        raise TypeError(
            "execution_attempt must be an ExecutionAttempt"
        )

    if not isinstance(capability, ExecutionCapability):
        raise TypeError(
            "capability must be an ExecutionCapability"
        )

    if not isinstance(adapter, EffectAdapter):
        raise TypeError(
            "adapter must satisfy EffectAdapter"
        )

    decision = execution_attempt.decision

    selected_effect = select_effect_for_custody(
        decision
    )

    validate_capability_for_custody(
        decision=decision,
        capability=capability,
    )

    result = adapter.execute(
        execution_attempt=execution_attempt,
        effect=selected_effect,
        capability=capability,
    )

    if not isinstance(result, AdapterExecutionResult):
        raise TypeError(
            "adapter must return an AdapterExecutionResult"
        )

    if result.execution_attempt != execution_attempt:
        raise AdapterResultMismatchError(
            "adapter result execution_attempt does not match "
            "custody execution_attempt"
        )

    return result