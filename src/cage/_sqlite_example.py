"""Disposable SQLite fixture for the source example and installed CLI."""

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability
from cage.adapters import AdapterExecutionResult, AdapterExecutionState
from cage.verifiers import EffectVerificationResult, VerificationState
from cage.warrants import dump_warrant, export_warrant


class SQLiteDeleteAdapter:
    def __init__(self, database: Path) -> None:
        self.database = database

    def execute(self, *, execution_attempt, effect, capability):
        record_id = effect.parameters["record_id"]
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "DELETE FROM records WHERE record_id = ?",
                (record_id,),
            )
        return AdapterExecutionResult(
            result_id=f"adapter_{uuid4().hex}",
            execution_attempt=execution_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("sqlite-delete-acknowledged",),
        )


class SQLiteStateVerifier:
    def __init__(self, database: Path, record_id: int) -> None:
        self.database = database
        self.record_id = record_id

    def verify(self, *, adapter_result):
        with closing(sqlite3.connect(self.database)) as connection:
            row = connection.execute(
                "SELECT record_id FROM records WHERE record_id = ?",
                (self.record_id,),
            ).fetchone()
        state = (
            VerificationState.VERIFIED_BOUND
            if row is None
            else VerificationState.VERIFIED_NO_BIND
        )
        return EffectVerificationResult(
            verification_id=f"verification_{uuid4().hex}",
            adapter_result=adapter_result,
            state=state,
            references=(
                f"sqlite-record-{self.record_id}-exists-{row is not None}",
            ),
        )


def main(*, warrant_path: str | Path | None = None) -> None:
    with TemporaryDirectory(prefix="cage-quickstart-") as directory:
        database = Path(directory) / "records.sqlite3"
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute(
                "CREATE TABLE records (record_id INTEGER PRIMARY KEY)"
            )
            connection.execute(
                "INSERT INTO records (record_id) VALUES (?)",
                (1,),
            )

        def evaluate_delete(
            attempt, evidence, standing, delegations, approvals, context
        ):
            action = attempt.consequence.action
            allowed = (
                action.action_type == "database.delete"
                and action.principal.principal_id == "local-operator"
                and action.resource.resource_id == "quickstart-records"
                and action.requested_effect.parameters["record_id"] == 1
            )
            return EvaluationOutcome(
                state=(
                    DecisionState.ADMITTED
                    if allowed
                    else DecisionState.REFUSED
                )
            )

        cage = CAGE(rule=evaluate_delete)
        action = cage.inputs.action(
            action_type="database.delete",
            principal_id="local-operator",
            agent_id="quickstart-agent",
            resource_id="quickstart-records",
            requested_effect={"record_id": 1},
        )
        evaluation = cage.evaluate(
            action=action,
            idempotency_key="quickstart-delete-record-1",
        )
        capability = ExecutionCapability(
            capability_id="quickstart-delete-capability",
            consequence_id=evaluation.consequence_id,
            action_type=action.action_type,
            resource_id=action.resource.resource_id,
        )
        execution = cage.execute(
            evaluation,
            adapter=SQLiteDeleteAdapter(database),
            capability=capability,
        )
        assurance = cage.verify(
            execution,
            verifier=SQLiteStateVerifier(database, record_id=1),
        )

        if warrant_path is not None:
            dump_warrant(export_warrant(assurance), warrant_path)

        print(f"Decision: {evaluation.decision.state.value}")
        print(f"Adapter: {execution.adapter_result.state.value}")
        print(f"Verification: {assurance.verification.state.value}")
        print(f"Effect: {assurance.effect.state.value}")
        print(f"Warrant ID: {assurance.warrant.warrant_id}")
