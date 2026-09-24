"""Disposable SQLite access grant fixture for the installed CLI."""

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability, RequestedEffect
from cage.adapters import AdapterExecutionResult, AdapterExecutionState
from cage.verifiers import EffectVerificationResult, VerificationState
from cage.warrants import dump_warrant, export_warrant


class SQLiteAccessAdapter:
    def __init__(self, database: Path) -> None:
        self.database = database

    def execute(self, *, execution_attempt, effect, capability):
        # Custody passes the narrowed effect, not the requested administrator role.
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "INSERT INTO grants (principal_id, role) VALUES (?, ?)",
                (effect.parameters["principal_id"], effect.parameters["role"]),
            )
        return AdapterExecutionResult(
            result_id=f"adapter_{uuid4().hex}", execution_attempt=execution_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("sqlite-access-grant-acknowledged",),
        )


class SQLiteAccessVerifier:
    def __init__(self, database: Path) -> None:
        self.database = database

    def verify(self, *, adapter_result):
        with closing(sqlite3.connect(self.database)) as connection:
            roles = tuple(row[0] for row in connection.execute(
                "SELECT role FROM grants WHERE principal_id = ?",
                ("local-reader",),
            ))
        state = (
            VerificationState.VERIFIED_BOUND if roles == ("reader",)
            else VerificationState.VERIFIED_NO_BIND
        )
        return EffectVerificationResult(
            verification_id=f"verification_{uuid4().hex}",
            adapter_result=adapter_result, state=state,
            references=(f"sqlite-access-roles-{','.join(roles) or 'none'}",),
        )


def main(*, warrant_path: str | Path | None = None) -> None:
    with TemporaryDirectory(prefix="cage-access-") as directory:
        database = Path(directory) / "access.sqlite3"
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute(
                "CREATE TABLE grants (principal_id TEXT NOT NULL, role TEXT NOT NULL)"
            )

        def evaluate_grant(
            attempt, evidence, standing, delegations, approvals, context
        ):
            action = attempt.consequence.action
            if (
                action.action_type != "access.grant"
                or action.principal.principal_id != "local-operator"
                or action.resource.resource_id != "local-access-records"
                or action.requested_effect.parameters != {
                    "principal_id": "local-reader", "role": "administrator"
                }
            ):
                return EvaluationOutcome(state=DecisionState.REFUSED)
            return EvaluationOutcome(
                state=DecisionState.NARROWED,
                permitted_effect=RequestedEffect({
                    "principal_id": "local-reader", "role": "reader",
                }),
            )

        cage = CAGE(rule=evaluate_grant)
        action = cage.inputs.action(
            action_type="access.grant", principal_id="local-operator",
            agent_id="access-example-agent", resource_id="local-access-records",
            requested_effect={"principal_id": "local-reader", "role": "administrator"},
        )
        evaluation = cage.evaluate(action=action, idempotency_key="access-grant-local-reader")
        capability = ExecutionCapability(
            capability_id="access-example-capability",
            consequence_id=evaluation.consequence_id,
            action_type=action.action_type, resource_id=action.resource.resource_id,
        )
        execution = cage.execute(
            evaluation, adapter=SQLiteAccessAdapter(database), capability=capability,
        )
        assurance = cage.verify(execution, verifier=SQLiteAccessVerifier(database))
        if warrant_path is not None:
            dump_warrant(export_warrant(assurance), warrant_path)

        print(f"Decision: {evaluation.decision.state.value}")
        print("Requested role: administrator")
        print(f"Permitted role: {evaluation.decision.permitted_effect.parameters['role']}")
        print(f"Adapter: {execution.adapter_result.state.value}")
        print(f"Verification: {assurance.verification.state.value}")
        print(f"Effect: {assurance.effect.state.value}")
        print(f"Warrant ID: {assurance.warrant.warrant_id}")
