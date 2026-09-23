"""Observe an uncertain SQLite delete again without re-executing it.

From an installed source checkout: python examples/sqlite_reconcile.py
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability
from cage.verifiers import EffectVerificationResult, VerificationState
from sqlite_delete import SQLiteDeleteAdapter, SQLiteStateVerifier


class CountingDeleteAdapter(SQLiteDeleteAdapter):
    def __init__(self, database: Path) -> None:
        super().__init__(database)
        self.calls = 0

    def execute(self, *, execution_attempt, effect, capability):
        self.calls += 1
        return super().execute(
            execution_attempt=execution_attempt,
            effect=effect,
            capability=capability,
        )


class TemporarilyUnavailableVerifier:
    def verify(self, *, adapter_result):
        # An acknowledgement is not evidence that the row was deleted.
        # This verifier has no authoritative observation yet.
        return EffectVerificationResult(
            verification_id=f"verification_{uuid4().hex}",
            adapter_result=adapter_result,
            state=VerificationState.INCONCLUSIVE,
        )


def main() -> None:
    with TemporaryDirectory(prefix="cage-reconcile-") as directory:
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
                and action.resource.resource_id == "reconcile-records"
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
            agent_id="reconciliation-agent",
            resource_id="reconcile-records",
            requested_effect={"record_id": 1},
        )
        evaluation = cage.evaluate(
            action=action,
            idempotency_key="reconcile-delete-record-1",
        )
        capability = ExecutionCapability(
            capability_id="reconcile-delete-capability",
            consequence_id=evaluation.consequence_id,
            action_type=action.action_type,
            resource_id=action.resource.resource_id,
        )
        adapter = CountingDeleteAdapter(database)
        execution = cage.execute(
            evaluation,
            adapter=adapter,
            capability=capability,
        )
        first = cage.verify(
            execution,
            verifier=TemporarilyUnavailableVerifier(),
        )
        later = cage.reconcile(
            first,
            verifier=SQLiteStateVerifier(database, record_id=1),
        )

        assert adapter.calls == 1
        assert first.warrant.warrant_id == later.warrant.previous_warrant_id

        print(f"First verification: {first.verification.state.value}")
        print(f"First effect: {first.effect.state.value}")
        print(f"Later verification: {later.verification.state.value}")
        print(f"Later effect: {later.effect.state.value}")
        print(f"Adapter dispatches: {adapter.calls}")
        print(f"Previous warrant ID: {first.warrant.warrant_id}")
        print(f"Later warrant predecessor: {later.warrant.previous_warrant_id}")


if __name__ == "__main__":
    main()
