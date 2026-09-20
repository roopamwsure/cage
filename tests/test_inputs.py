import pytest

from cage.core.action import Action, RequestedEffect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.identity import Agent, Principal, Resource
from cage.errors import (
    CAGETypeError,
    CAGEValueError,
    IdentifierGenerationError,
)
from cage.identifiers import IdentityKind
from cage.inputs import CAGEInputs


def test_action_helper_generates_action_id_and_core_objects() -> None:
    requested_kinds: list[IdentityKind] = []

    def deterministic_id(kind: IdentityKind) -> str:
        requested_kinds.append(kind)
        return f"generated_{kind.value}"

    inputs = CAGEInputs(id_factory=deterministic_id)

    action = inputs.action(
        action_type="database.delete",
        principal_id="principal-123",
        agent_id="agent-456",
        resource_id="record-789",
        requested_effect={"table": "accounts", "record_id": 789},
    )

    assert type(action) is Action
    assert type(action.principal) is Principal
    assert type(action.agent) is Agent
    assert type(action.resource) is Resource
    assert type(action.requested_effect) is RequestedEffect

    assert action.action_id == "generated_action"
    assert action.action_type == "database.delete"
    assert action.principal.principal_id == "principal-123"
    assert action.agent.agent_id == "agent-456"
    assert action.resource.resource_id == "record-789"
    assert action.requested_effect.parameters == {
        "table": "accounts",
        "record_id": 789,
    }
    assert requested_kinds == [IdentityKind.ACTION]


def test_action_helper_preserves_explicit_action_id() -> None:
    factory_called = False

    def unexpected_factory(kind: IdentityKind) -> str:
        nonlocal factory_called
        factory_called = True
        return f"unexpected_{kind.value}"

    inputs = CAGEInputs(id_factory=unexpected_factory)

    action = inputs.action(
        action_id="action-explicit",
        action_type="access.grant",
        principal_id="principal-123",
        agent_id="agent-456",
        resource_id="resource-789",
        requested_effect={"role": "reader"},
    )

    assert action.action_id == "action-explicit"
    assert factory_called is False


def test_action_helper_delegates_validation_to_core_contracts() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: f"generated_{kind.value}")

    with pytest.raises(ValueError, match="action_type must not be empty"):
        inputs.action(
            action_type="   ",
            principal_id="principal-123",
            agent_id="agent-456",
            resource_id="resource-789",
            requested_effect={"operation": "delete"},
        )


@pytest.mark.parametrize("invalid_factory", [None, "factory", 42, object()])
def test_inputs_reject_noncallable_factory(invalid_factory: object) -> None:
    with pytest.raises(CAGETypeError, match="id_factory must be callable"):
        CAGEInputs(id_factory=invalid_factory)  # type: ignore[arg-type]


def test_action_helper_rejects_non_string_generated_id() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: 42)  # type: ignore[arg-type]

    with pytest.raises(
        CAGETypeError,
        match="id_factory must return a string for action",
    ):
        inputs.action(
            action_type="database.delete",
            principal_id="principal-123",
            agent_id="agent-456",
            resource_id="record-789",
            requested_effect={"operation": "delete"},
        )


def test_action_helper_rejects_blank_generated_id() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: "   ")

    with pytest.raises(
        CAGEValueError,
        match="id_factory must return a nonblank string for action",
    ):
        inputs.action(
            action_type="database.delete",
            principal_id="principal-123",
            agent_id="agent-456",
            resource_id="record-789",
            requested_effect={"operation": "delete"},
        )


def test_action_helper_wraps_factory_exception_with_identity_context() -> None:
    cause = RuntimeError("provider-specific sensitive detail")

    def failing_factory(kind: IdentityKind) -> str:
        raise cause

    inputs = CAGEInputs(id_factory=failing_factory)

    with pytest.raises(
        IdentifierGenerationError,
        match="failed to generate action identifier",
    ) as captured:
        inputs.action(
            action_type="database.delete",
            principal_id="principal-123",
            agent_id="agent-456",
            resource_id="record-789",
            requested_effect={"operation": "delete"},
        )

    assert captured.value.kind is IdentityKind.ACTION
    assert captured.value.__cause__ is cause
    assert str(cause) not in str(captured.value)


def test_evidence_helper_generates_id_and_core_object() -> None:
    requested_kinds: list[IdentityKind] = []

    def deterministic_id(kind: IdentityKind) -> str:
        requested_kinds.append(kind)
        return f"generated_{kind.value}"

    inputs = CAGEInputs(id_factory=deterministic_id)

    evidence = inputs.evidence(
        evidence_type="approval.ticket",
        subject="database.delete",
        source="change-management",
        data={"ticket": "CHG-123", "approved": True},
    )

    assert type(evidence) is Evidence
    assert evidence.evidence_id == "generated_evidence"
    assert evidence.evidence_type == "approval.ticket"
    assert evidence.subject == "database.delete"
    assert evidence.source == "change-management"
    assert evidence.data == {
        "ticket": "CHG-123",
        "approved": True,
    }
    assert requested_kinds == [IdentityKind.EVIDENCE]


def test_evidence_helper_preserves_explicit_id() -> None:
    factory_called = False

    def unexpected_factory(kind: IdentityKind) -> str:
        nonlocal factory_called
        factory_called = True
        return f"unexpected_{kind.value}"

    inputs = CAGEInputs(id_factory=unexpected_factory)

    evidence = inputs.evidence(
        evidence_id="evidence-explicit",
        evidence_type="approval.ticket",
        subject="database.delete",
        source="change-management",
        data={"ticket": "CHG-123"},
    )

    assert evidence.evidence_id == "evidence-explicit"
    assert factory_called is False
def test_standing_helper_generates_id_and_core_object() -> None:
    requested_kinds: list[IdentityKind] = []

    def deterministic_id(kind: IdentityKind) -> str:
        requested_kinds.append(kind)
        return f"generated_{kind.value}"

    inputs = CAGEInputs(id_factory=deterministic_id)

    standing = inputs.standing(
        standing_type="employment",
        subject="principal-123",
        source="identity-directory",
        attributes={"department": "finance", "active": True},
    )

    assert type(standing) is Standing
    assert standing.standing_id == "generated_standing"
    assert standing.standing_type == "employment"
    assert standing.subject == "principal-123"
    assert standing.source == "identity-directory"
    assert standing.attributes == {
        "department": "finance",
        "active": True,
    }
    assert requested_kinds == [IdentityKind.STANDING]


def test_standing_helper_preserves_explicit_id() -> None:
    factory_called = False

    def unexpected_factory(kind: IdentityKind) -> str:
        nonlocal factory_called
        factory_called = True
        return f"unexpected_{kind.value}"

    inputs = CAGEInputs(id_factory=unexpected_factory)

    standing = inputs.standing(
        standing_id="standing-explicit",
        standing_type="employment",
        subject="principal-123",
        source="identity-directory",
        attributes={"department": "finance"},
    )

    assert standing.standing_id == "standing-explicit"
    assert factory_called is False
def test_delegation_helper_generates_id_and_core_object() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: f"generated_{kind.value}")

    delegation = inputs.delegation(
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-service",
        scope={"action_type": "database.delete"},
    )

    assert type(delegation) is Delegation
    assert delegation.delegation_id == "generated_delegation"
    assert delegation.delegator == "principal-123"
    assert delegation.delegatee == "agent-456"
    assert delegation.source == "delegation-service"
    assert delegation.scope == {"action_type": "database.delete"}


def test_delegation_helper_preserves_explicit_id() -> None:
    inputs = CAGEInputs(
        id_factory=lambda kind: (_ for _ in ()).throw(
            AssertionError("factory must not be called")
        )
    )

    delegation = inputs.delegation(
        delegation_id="delegation-explicit",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-service",
        scope={"action_type": "database.delete"},
    )

    assert delegation.delegation_id == "delegation-explicit"


def test_approval_helper_generates_id_and_core_object() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: f"generated_{kind.value}")

    approval = inputs.approval(
        approval_type="human.review",
        approver="reviewer-123",
        subject="database.delete",
        source="approval-service",
        scope={"resource_id": "record-789"},
    )

    assert type(approval) is Approval
    assert approval.approval_id == "generated_approval"
    assert approval.approval_type == "human.review"
    assert approval.approver == "reviewer-123"
    assert approval.subject == "database.delete"
    assert approval.source == "approval-service"
    assert approval.scope == {"resource_id": "record-789"}


def test_approval_helper_preserves_explicit_id() -> None:
    inputs = CAGEInputs(
        id_factory=lambda kind: (_ for _ in ()).throw(
            AssertionError("factory must not be called")
        )
    )

    approval = inputs.approval(
        approval_id="approval-explicit",
        approval_type="human.review",
        approver="reviewer-123",
        subject="database.delete",
        source="approval-service",
        scope={"resource_id": "record-789"},
    )

    assert approval.approval_id == "approval-explicit"


def test_context_helper_generates_id_and_core_object() -> None:
    inputs = CAGEInputs(id_factory=lambda kind: f"generated_{kind.value}")

    context = inputs.context(
        context_type="request.environment",
        source="application",
        values={"environment": "production", "risk": "high"},
    )

    assert type(context) is Context
    assert context.context_id == "generated_context"
    assert context.context_type == "request.environment"
    assert context.source == "application"
    assert context.values == {
        "environment": "production",
        "risk": "high",
    }


def test_context_helper_preserves_explicit_id() -> None:
    inputs = CAGEInputs(
        id_factory=lambda kind: (_ for _ in ()).throw(
            AssertionError("factory must not be called")
        )
    )

    context = inputs.context(
        context_id="context-explicit",
        context_type="request.environment",
        source="application",
        values={"environment": "production"},
    )

    assert context.context_id == "context-explicit"
