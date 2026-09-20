from collections.abc import Mapping

from cage.core.action import Action, RequestedEffect
from cage.core.assurance import (
    Approval,
    Context,
    Delegation,
    Evidence,
    Standing,
)
from cage.core.identity import Agent, Principal, Resource
from cage.errors import CAGETypeError
from cage.identifiers import IdentityKind, IdFactory, _generate_id


class CAGEInputs:
    """Construct existing CAGE core inputs with generated record IDs."""

    __slots__ = ("_id_factory",)

    def __init__(self, *, id_factory: IdFactory) -> None:
        if not callable(id_factory):
            raise CAGETypeError("id_factory must be callable")

        self._id_factory = id_factory

    def action(
        self,
        *,
        action_type: str,
        principal_id: str,
        agent_id: str,
        resource_id: str,
        requested_effect: Mapping[str, object],
        action_id: str | None = None,
    ) -> Action:
        resolved_action_id = (
            _generate_id(self._id_factory, IdentityKind.ACTION)
            if action_id is None
            else action_id
        )

        return Action(
            action_id=resolved_action_id,
            action_type=action_type,
            principal=Principal(principal_id=principal_id),
            agent=Agent(agent_id=agent_id),
            resource=Resource(resource_id=resource_id),
            requested_effect=RequestedEffect(parameters=requested_effect),
        )

    def evidence(
        self,
        *,
        evidence_type: str,
        subject: str,
        source: str,
        data: Mapping[str, object],
        evidence_id: str | None = None,
    ) -> Evidence:
        resolved_evidence_id = (
            _generate_id(self._id_factory, IdentityKind.EVIDENCE)
            if evidence_id is None
            else evidence_id
        )

        return Evidence(
            evidence_id=resolved_evidence_id,
            evidence_type=evidence_type,
            subject=subject,
            source=source,
            data=data,
        )

    def standing(
        self,
        *,
        standing_type: str,
        subject: str,
        source: str,
        attributes: Mapping[str, object],
        standing_id: str | None = None,
    ) -> Standing:
        resolved_standing_id = (
            _generate_id(self._id_factory, IdentityKind.STANDING)
            if standing_id is None
            else standing_id
        )

        return Standing(
            standing_id=resolved_standing_id,
            standing_type=standing_type,
            subject=subject,
            source=source,
            attributes=attributes,
        )

    def delegation(
        self,
        *,
        delegator: str,
        delegatee: str,
        source: str,
        scope: Mapping[str, object],
        delegation_id: str | None = None,
    ) -> Delegation:
        resolved_delegation_id = (
            _generate_id(self._id_factory, IdentityKind.DELEGATION)
            if delegation_id is None
            else delegation_id
        )

        return Delegation(
            delegation_id=resolved_delegation_id,
            delegator=delegator,
            delegatee=delegatee,
            source=source,
            scope=scope,
        )

    def approval(
        self,
        *,
        approval_type: str,
        approver: str,
        subject: str,
        source: str,
        scope: Mapping[str, object],
        approval_id: str | None = None,
    ) -> Approval:
        resolved_approval_id = (
            _generate_id(self._id_factory, IdentityKind.APPROVAL)
            if approval_id is None
            else approval_id
        )

        return Approval(
            approval_id=resolved_approval_id,
            approval_type=approval_type,
            approver=approver,
            subject=subject,
            source=source,
            scope=scope,
        )

    def context(
        self,
        *,
        context_type: str,
        source: str,
        values: Mapping[str, object],
        context_id: str | None = None,
    ) -> Context:
        resolved_context_id = (
            _generate_id(self._id_factory, IdentityKind.CONTEXT)
            if context_id is None
            else context_id
        )

        return Context(
            context_id=resolved_context_id,
            context_type=context_type,
            source=source,
            values=values,
        )