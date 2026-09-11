import pytest

from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)


def test_evidence_accepts_generic_data() -> None:
    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="change_approval",
        subject="consequence-001",
        source="approval-system",
        data={
            "ticket": "CHG-12345",
            "approved": True,
        },
    )

    assert evidence.evidence_id == "evidence-001"
    assert evidence.data["approved"] is True


def test_evidence_supports_different_sources() -> None:
    identity_evidence = Evidence(
        evidence_id="evidence-identity",
        evidence_type="identity_assertion",
        subject="agent-123",
        source="identity-provider",
        data={"authenticated": True},
    )

    target_evidence = Evidence(
        evidence_id="evidence-target",
        evidence_type="target_state",
        subject="database-123",
        source="database-controller",
        data={"exists": True},
    )

    assert identity_evidence.evidence_type == "identity_assertion"
    assert target_evidence.evidence_type == "target_state"


def test_evidence_data_cannot_be_modified() -> None:
    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="target_state",
        subject="database-123",
        source="database-controller",
        data={"exists": True},
    )

    with pytest.raises(TypeError):
        evidence.data["exists"] = False


def test_evidence_isolated_from_original_data() -> None:
    data = {"approved": True}

    evidence = Evidence(
        evidence_id="evidence-001",
        evidence_type="approval",
        subject="consequence-001",
        source="approval-system",
        data=data,
    )

    data["approved"] = False

    assert evidence.data["approved"] is True


@pytest.mark.parametrize(
    "field_name",
    [
        "evidence_id",
        "evidence_type",
        "subject",
        "source",
    ],
)
def test_evidence_requires_non_empty_identity_fields(
    field_name: str,
) -> None:
    values = {
        "evidence_id": "evidence-001",
        "evidence_type": "approval",
        "subject": "consequence-001",
        "source": "approval-system",
        "data": {},
    }

    values[field_name] = "   "

    with pytest.raises(ValueError):
        Evidence(**values)


def test_evidence_rejects_arbitrary_python_objects() -> None:
    with pytest.raises(TypeError):
        Evidence(
            evidence_id="evidence-001",
            evidence_type="custom",
            subject="consequence-001",
            source="external-system",
            data={"invalid": object()},
        )

def test_standing_accepts_generic_attributes() -> None:
    standing = Standing(
        standing_id="standing-001",
        standing_type="operational_authority",
        subject="agent-456",
        source="entitlement-system",
        attributes={
            "environments": ["development", "staging"],
            "destructive_actions": False,
        },
    )

    assert standing.standing_type == "operational_authority"
    assert standing.attributes["destructive_actions"] is False


def test_standing_supports_different_domains() -> None:
    database_standing = Standing(
        standing_id="standing-db",
        standing_type="operational_authority",
        subject="agent-456",
        source="entitlement-system",
        attributes={
            "environments": ["development"],
        },
    )

    access_standing = Standing(
        standing_id="standing-access",
        standing_type="privileged_access",
        subject="principal-123",
        source="access-system",
        attributes={
            "allowed_roles": ["operator"],
            "max_duration_minutes": 30,
        },
    )

    payment_standing = Standing(
        standing_id="standing-payment",
        standing_type="transaction_authority",
        subject="principal-123",
        source="financial-control-system",
        attributes={
            "transaction_class": "domestic",
            "configured_limit": 10000,
        },
    )

    assert database_standing.attributes["environments"] == ("development",)
    assert access_standing.attributes["max_duration_minutes"] == 30
    assert payment_standing.attributes["configured_limit"] == 10000


def test_standing_attributes_cannot_be_modified() -> None:
    standing = Standing(
        standing_id="standing-001",
        standing_type="operational_authority",
        subject="agent-456",
        source="entitlement-system",
        attributes={"destructive_actions": False},
    )

    with pytest.raises(TypeError):
        standing.attributes["destructive_actions"] = True


def test_standing_isolated_from_original_attributes() -> None:
    attributes = {"max_duration_minutes": 30}

    standing = Standing(
        standing_id="standing-001",
        standing_type="privileged_access",
        subject="principal-123",
        source="access-system",
        attributes=attributes,
    )

    attributes["max_duration_minutes"] = 120

    assert standing.attributes["max_duration_minutes"] == 30


@pytest.mark.parametrize(
    "field_name",
    [
        "standing_id",
        "standing_type",
        "subject",
        "source",
    ],
)
def test_standing_requires_non_empty_identity_fields(
    field_name: str,
) -> None:
    values = {
        "standing_id": "standing-001",
        "standing_type": "operational_authority",
        "subject": "agent-456",
        "source": "entitlement-system",
        "attributes": {},
    }

    values[field_name] = "   "

    with pytest.raises(ValueError):
        Standing(**values)


def test_standing_rejects_arbitrary_python_objects() -> None:
    with pytest.raises(TypeError):
        Standing(
            standing_id="standing-001",
            standing_type="custom",
            subject="agent-456",
            source="external-system",
            attributes={"invalid": object()},
        )

def test_delegation_represents_generic_authority_transfer() -> None:
    delegation = Delegation(
        delegation_id="delegation-001",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-system",
        scope={
            "environments": ["development", "staging"],
            "actions": ["database.read", "database.backup"],
        },
    )

    assert delegation.delegator == "principal-123"
    assert delegation.delegatee == "agent-456"
    assert delegation.scope["environments"] == (
        "development",
        "staging",
    )


def test_delegation_supports_different_domains() -> None:
    access_delegation = Delegation(
        delegation_id="delegation-access",
        delegator="principal-123",
        delegatee="agent-456",
        source="access-system",
        scope={
            "roles": ["operator"],
            "max_duration_minutes": 30,
        },
    )

    payment_delegation = Delegation(
        delegation_id="delegation-payment",
        delegator="principal-123",
        delegatee="agent-456",
        source="financial-control-system",
        scope={
            "transaction_class": "domestic",
            "configured_limit": 10000,
        },
    )

    assert access_delegation.scope["max_duration_minutes"] == 30
    assert payment_delegation.scope["configured_limit"] == 10000


def test_delegation_scope_cannot_be_modified() -> None:
    delegation = Delegation(
        delegation_id="delegation-001",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-system",
        scope={"environment": "development"},
    )

    with pytest.raises(TypeError):
        delegation.scope["environment"] = "production"


def test_delegation_isolated_from_original_scope() -> None:
    scope = {"max_duration_minutes": 30}

    delegation = Delegation(
        delegation_id="delegation-001",
        delegator="principal-123",
        delegatee="agent-456",
        source="delegation-system",
        scope=scope,
    )

    scope["max_duration_minutes"] = 120

    assert delegation.scope["max_duration_minutes"] == 30


@pytest.mark.parametrize(
    "field_name",
    [
        "delegation_id",
        "delegator",
        "delegatee",
        "source",
    ],
)
def test_delegation_requires_non_empty_identity_fields(
    field_name: str,
) -> None:
    values = {
        "delegation_id": "delegation-001",
        "delegator": "principal-123",
        "delegatee": "agent-456",
        "source": "delegation-system",
        "scope": {},
    }

    values[field_name] = "   "

    with pytest.raises(ValueError):
        Delegation(**values)


def test_delegation_rejects_arbitrary_python_objects() -> None:
    with pytest.raises(TypeError):
        Delegation(
            delegation_id="delegation-001",
            delegator="principal-123",
            delegatee="agent-456",
            source="delegation-system",
            scope={"invalid": object()},
        )                

def test_approval_represents_specific_authorization() -> None:
    approval = Approval(
        approval_id="approval-001",
        approval_type="change_authorization",
        approver="principal-789",
        subject="consequence-001",
        source="approval-system",
        scope={
            "environment": "production",
            "action": "database.delete",
        },
    )

    assert approval.approver == "principal-789"
    assert approval.subject == "consequence-001"
    assert approval.scope["environment"] == "production"


def test_approval_supports_different_domains() -> None:
    access_approval = Approval(
        approval_id="approval-access",
        approval_type="privileged_access",
        approver="principal-security",
        subject="consequence-access",
        source="access-system",
        scope={
            "role": "operator",
            "duration_minutes": 30,
        },
    )

    payment_approval = Approval(
        approval_id="approval-payment",
        approval_type="transaction_authorization",
        approver="principal-finance",
        subject="consequence-payment",
        source="financial-control-system",
        scope={
            "currency": "USD",
            "amount_limit": 10000,
        },
    )

    assert access_approval.scope["duration_minutes"] == 30
    assert payment_approval.scope["amount_limit"] == 10000


def test_approval_scope_cannot_be_modified() -> None:
    approval = Approval(
        approval_id="approval-001",
        approval_type="change_authorization",
        approver="principal-789",
        subject="consequence-001",
        source="approval-system",
        scope={"environment": "production"},
    )

    with pytest.raises(TypeError):
        approval.scope["environment"] = "development"


@pytest.mark.parametrize(
    "field_name",
    [
        "approval_id",
        "approval_type",
        "approver",
        "subject",
        "source",
    ],
)
def test_approval_requires_non_empty_identity_fields(
    field_name: str,
) -> None:
    values = {
        "approval_id": "approval-001",
        "approval_type": "change_authorization",
        "approver": "principal-789",
        "subject": "consequence-001",
        "source": "approval-system",
        "scope": {},
    }

    values[field_name] = "   "

    with pytest.raises(ValueError):
        Approval(**values)        