from threading import Event, Thread

import pytest

from cage._facade import CAGE
from cage.core.action import RequestedEffect
from cage.core.adapter import AdapterExecutionResult, AdapterExecutionState
from cage.core.capability import ExecutionCapability
from cage.core.decision import DecisionState
from cage.core.effect import EffectState
from cage.core.evaluation import EvaluationOutcome
from cage.core.execution import ExecutionAttempt
from cage.core.verification import EffectVerificationResult, VerificationState
from cage.errors import (
    AssuranceAssemblyError,
    CAGEValueError,
    IdentityConflictError,
    DuplicateReconciliationError,
    VerifierInvocationError,
)
from cage.identifiers import AssuranceIds


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        self.calls += 1
        return AdapterExecutionResult(
            result_id="adapter-result-1",
            execution_attempt=execution_attempt,
            state=AdapterExecutionState.ACKNOWLEDGED,
            references=("receipt-1",),
        )


class RecordingVerifier:
    def __init__(self) -> None:
        self.calls: list[AdapterExecutionResult] = []

    def verify(
        self,
        *,
        adapter_result: AdapterExecutionResult,
    ) -> EffectVerificationResult:
        self.calls.append(adapter_result)
        return EffectVerificationResult(
            verification_id=f"verification-{len(self.calls)}",
            adapter_result=adapter_result,
            state=VerificationState.INCONCLUSIVE,
        )


def test_reconcile_links_to_previous_assurance_without_dispatch() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-record-1",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = RecordingVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )

    current = cage.reconcile(
        previous,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-2",
            effect_proof_id="effect-proof-2",
            warrant_id="warrant-2",
        ),
    )

    assert adapter.calls == 1
    assert verifier.calls == [execution.adapter_result] * 2
    assert current.execution is execution
    assert current.warrant.previous_warrant_id == previous.warrant.warrant_id
    assert current.warrant.warrant_id == "warrant-2"
    assert current.verification.verification_id == "verification-2"
    assert current.effect.effect_id == "effect-2"
    assert current.effect_proof.proof_id == "effect-proof-2"
    assert previous.warrant.warrant_id == "warrant-1"


def test_reconcile_verifier_failure_retains_previous_assurance() -> None:
    class FailingVerifier:
        def __init__(self) -> None:
            self.calls: list[AdapterExecutionResult] = []
            self.failure = RuntimeError("observation unavailable")

        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            self.calls.append(adapter_result)
            raise self.failure

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-verifier-failure",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    previous = cage.verify(
        execution,
        verifier=RecordingVerifier(),
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    verifier = FailingVerifier()

    with pytest.raises(VerifierInvocationError) as captured:
        cage.reconcile(
            previous,
            verifier=verifier,
            ids=AssuranceIds(
                effect_id="effect-2",
                effect_proof_id="effect-proof-2",
                warrant_id="warrant-2",
            ),
        )

    assert verifier.calls == [execution.adapter_result]
    assert adapter.calls == 1
    assert captured.value.execution is execution
    assert captured.value.previous is previous
    assert captured.value.__cause__ is verifier.failure
    assert previous.warrant.warrant_id == "warrant-1"

    class RetryVerifier:
        def verify(self, *, adapter_result):
            return EffectVerificationResult(
                verification_id="verification-retry",
                adapter_result=adapter_result,
                state=VerificationState.INCONCLUSIVE,
            )

    recovered = cage.reconcile(
        previous,
        verifier=RetryVerifier(),
        ids=AssuranceIds(
            effect_id="effect-retry",
            effect_proof_id="effect-proof-retry",
            warrant_id="warrant-retry",
        ),
    )
    assert recovered.warrant.previous_warrant_id == previous.warrant.warrant_id


def test_reconcile_rejects_previous_warrant_id_before_verification() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-previous-warrant-id",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = RecordingVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )

    with pytest.raises(
        IdentityConflictError,
        match="warrant_id must differ from previous warrant_id",
    ):
        cage.reconcile(
            previous,
            verifier=verifier,
            ids=AssuranceIds(
                effect_id="effect-2",
                effect_proof_id="effect-proof-2",
                warrant_id="warrant-1",
            ),
        )

    assert verifier.calls == [execution.adapter_result]
    assert adapter.calls == 1
    assert previous.warrant.warrant_id == "warrant-1"


@pytest.mark.parametrize(
    ("reused_id", "expected_message"),
    [
        ("effect", "effect_id must differ from previous effect_id"),
        (
            "effect_proof",
            "effect_proof_id must differ from previous effect_proof_id",
        ),
    ],
)
def test_reconcile_rejects_previous_effect_identities_before_verification(
    reused_id: str,
    expected_message: str,
) -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key=f"reconcile-previous-{reused_id}-id",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = RecordingVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    ids = AssuranceIds(
        effect_id="effect-1" if reused_id == "effect" else "effect-2",
        effect_proof_id=(
            "effect-proof-1"
            if reused_id == "effect_proof"
            else "effect-proof-2"
        ),
        warrant_id="warrant-2",
    )

    with pytest.raises(IdentityConflictError, match=expected_message):
        cage.reconcile(previous, verifier=verifier, ids=ids)

    assert verifier.calls == [execution.adapter_result]
    assert adapter.calls == 1


def test_reconcile_can_establish_bound_effect_after_inconclusive() -> None:
    class LaterBoundVerifier:
        def __init__(self) -> None:
            self.calls: list[AdapterExecutionResult] = []

        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            self.calls.append(adapter_result)
            if len(self.calls) == 1:
                return EffectVerificationResult(
                    verification_id="verification-inconclusive",
                    adapter_result=adapter_result,
                    state=VerificationState.INCONCLUSIVE,
                )
            return EffectVerificationResult(
                verification_id="verification-bound",
                adapter_result=adapter_result,
                state=VerificationState.VERIFIED_BOUND,
                references=("later-authoritative-observation",),
            )

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-later-bound",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = LaterBoundVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    current = cage.reconcile(
        previous,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-2",
            effect_proof_id="effect-proof-2",
            warrant_id="warrant-2",
        ),
    )

    assert adapter.calls == 1
    assert verifier.calls == [execution.adapter_result] * 2
    assert previous.effect.state is EffectState.EFFECT_UNKNOWN
    assert previous.verification.state is VerificationState.INCONCLUSIVE
    assert previous.warrant.previous_warrant_id == evaluation.warrant.warrant_id
    assert current.execution is execution
    assert current.effect.state is EffectState.BOUND
    assert current.effect.verification_refs == (
        "later-authoritative-observation",
    )
    assert current.warrant.previous_warrant_id == previous.warrant.warrant_id


def test_reconcile_assembly_failure_retains_previous_and_verification(
    monkeypatch,
) -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-assembly-failure",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = RecordingVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    verification_seen: list[EffectVerificationResult] = []
    failure = ValueError("effect assembly failed")

    def fail_effect(*, effect_id, verification):
        assert effect_id == "effect-2"
        verification_seen.append(verification)
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(
            "cage._facade.create_effect_from_verification",
            fail_effect,
        )
        with pytest.raises(AssuranceAssemblyError) as captured:
            cage.reconcile(
                previous,
                verifier=verifier,
                ids=AssuranceIds(
                    effect_id="effect-2",
                    effect_proof_id="effect-proof-2",
                    warrant_id="warrant-2",
                ),
            )

    assert adapter.calls == 1
    assert verifier.calls == [execution.adapter_result] * 2
    assert captured.value.execution is execution
    assert captured.value.previous is previous
    assert captured.value.verification is verification_seen[0]
    assert captured.value.stage == "effect"
    assert captured.value.__cause__ is failure
    assert previous.warrant.warrant_id == "warrant-1"


def test_reconcile_rejects_second_successor_of_same_warrant() -> None:
    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-single-successor",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    verifier = RecordingVerifier()
    previous = cage.verify(
        execution,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    successor = cage.reconcile(
        previous,
        verifier=verifier,
        ids=AssuranceIds(
            effect_id="effect-2",
            effect_proof_id="effect-proof-2",
            warrant_id="warrant-2",
        ),
    )

    with pytest.raises(DuplicateReconciliationError) as captured:
        cage.reconcile(previous, verifier=verifier)

    assert captured.value.previous is previous
    assert captured.value.assurance is successor
    assert adapter.calls == 1
    assert verifier.calls == [execution.adapter_result] * 2


def test_reconcile_rejects_concurrent_successor_of_same_warrant() -> None:
    class BlockingVerifier(RecordingVerifier):
        def __init__(self) -> None:
            super().__init__()
            self.entered = Event()
            self.release = Event()

        def verify(
            self,
            *,
            adapter_result: AdapterExecutionResult,
        ) -> EffectVerificationResult:
            self.entered.set()
            if not self.release.wait(timeout=5):
                raise TimeoutError("verifier was not released")
            return super().verify(adapter_result=adapter_result)

    cage = CAGE(
        rule=lambda *args: EvaluationOutcome(
            state=DecisionState.ADMITTED
        )
    )
    action = cage.inputs.action(
        action_type="database.delete",
        principal_id="principal-1",
        agent_id="agent-1",
        resource_id="record-1",
        requested_effect={"record_id": 1},
    )
    evaluation = cage.evaluate(
        action=action,
        idempotency_key="reconcile-concurrent-successor",
    )
    capability = ExecutionCapability(
        capability_id="capability-1",
        consequence_id=evaluation.consequence_id,
        action_type="database.delete",
        resource_id="record-1",
    )
    adapter = RecordingAdapter()
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
    previous = cage.verify(
        execution,
        verifier=RecordingVerifier(),
        ids=AssuranceIds(
            effect_id="effect-1",
            effect_proof_id="effect-proof-1",
            warrant_id="warrant-1",
        ),
    )
    verifier = BlockingVerifier()
    results = []
    errors: list[BaseException] = []

    def first_call() -> None:
        try:
            results.append(cage.reconcile(previous, verifier=verifier))
        except BaseException as error:
            errors.append(error)

    thread = Thread(target=first_call)
    thread.start()
    try:
        assert verifier.entered.wait(timeout=5)
        with pytest.raises(DuplicateReconciliationError) as captured:
            cage.reconcile(previous, verifier=verifier)
        assert captured.value.previous is previous
        assert captured.value.assurance is None
        assert verifier.calls == []
    finally:
        verifier.release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []
    assert len(results) == 1
    assert adapter.calls == 1
    assert verifier.calls == [execution.adapter_result]
