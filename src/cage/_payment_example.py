"""Disposable simulated payment ledger for uncertain-effect reconciliation."""

from pathlib import Path
from uuid import uuid4

from cage import CAGE, DecisionState, EvaluationOutcome, ExecutionCapability
from cage.adapters import AdapterExecutionResult, AdapterExecutionState
from cage.verifiers import EffectVerificationResult, VerificationState
from cage.warrants import dump_warrant, export_warrant


class SimulatedLedgerAdapter:
    def __init__(self, ledger: dict[str, int]) -> None:
        self.ledger = ledger
        self.dispatches = 0

    def execute(self, *, execution_attempt, effect, capability):
        self.dispatches += 1
        invoice_id = effect.parameters["invoice_id"]
        self.ledger[invoice_id] = effect.parameters["amount_cents"]
        # The write took place, but the simulated acknowledgement is unavailable.
        return AdapterExecutionResult(
            result_id=f"adapter_{uuid4().hex}", execution_attempt=execution_attempt,
            state=AdapterExecutionState.UNKNOWN,
            references=("simulated-ledger-acknowledgement-unavailable",),
        )


class LedgerVerifier:
    def __init__(self, ledger: dict[str, int], *, visible: bool) -> None:
        self.ledger = ledger
        self.visible = visible

    def verify(self, *, adapter_result):
        if not self.visible:
            state = VerificationState.INCONCLUSIVE
            references: tuple[str, ...] = ()
        else:
            recorded = self.ledger.get("invoice-1")
            state = (
                VerificationState.VERIFIED_BOUND if recorded == 2500
                else VerificationState.VERIFIED_NO_BIND
            )
            references = (f"simulated-ledger-invoice-1-amount-{recorded}",)
        return EffectVerificationResult(
            verification_id=f"verification_{uuid4().hex}",
            adapter_result=adapter_result, state=state, references=references,
        )


def main(*, warrant_path: str | Path | None = None) -> None:
    ledger: dict[str, int] = {}

    def evaluate_release(
        attempt, evidence, standing, delegations, approvals, context
    ):
        action = attempt.consequence.action
        allowed = (
            action.action_type == "payment.release"
            and action.principal.principal_id == "local-operator"
            and action.resource.resource_id == "simulated-ledger"
            and action.requested_effect.parameters == {
                "invoice_id": "invoice-1", "amount_cents": 2500,
            }
        )
        return EvaluationOutcome(
            state=DecisionState.ADMITTED if allowed else DecisionState.REFUSED,
        )

    cage = CAGE(rule=evaluate_release)
    action = cage.inputs.action(
        action_type="payment.release", principal_id="local-operator",
        agent_id="payment-example-agent", resource_id="simulated-ledger",
        requested_effect={"invoice_id": "invoice-1", "amount_cents": 2500},
    )
    evaluation = cage.evaluate(action=action, idempotency_key="release-invoice-1")
    capability = ExecutionCapability(
        capability_id="payment-example-capability",
        consequence_id=evaluation.consequence_id,
        action_type=action.action_type, resource_id=action.resource.resource_id,
    )
    adapter = SimulatedLedgerAdapter(ledger)
    execution = cage.execute(evaluation, adapter=adapter, capability=capability)
    previous = cage.verify(
        execution, verifier=LedgerVerifier(ledger, visible=False),
    )
    current = cage.reconcile(
        previous, verifier=LedgerVerifier(ledger, visible=True),
    )

    if (
        adapter.dispatches != 1
        or previous.effect.state.value != "effect_unknown"
        or current.effect.state.value != "bound"
        or current.warrant.previous_warrant_id != previous.warrant.warrant_id
    ):
        raise RuntimeError("payment example did not establish expected lineage")

    if warrant_path is not None:
        dump_warrant(export_warrant(current), warrant_path)

    print(f"Decision: {evaluation.decision.state.value}")
    print(f"Adapter: {execution.adapter_result.state.value}")
    print(f"First verification: {previous.verification.state.value}")
    print(f"First effect: {previous.effect.state.value}")
    print(f"Later verification: {current.verification.state.value}")
    print(f"Later effect: {current.effect.state.value}")
    print(f"Adapter dispatches: {adapter.dispatches}")
    print(f"Previous warrant ID: {previous.warrant.warrant_id}")
    print(f"Later warrant predecessor: {current.warrant.previous_warrant_id}")
