# Integrating CAGE v0.7

This guide covers application-owned rules, adapters, verifiers, failures, and
trust boundaries. For a runnable local sequence, start with the
[Quickstart](quickstart.md); for the exact signatures and import map, see the
[public API](v0.7-public-api.md). The examples use disposable fixtures. None
of them is a production payment, access-control, or database integration.
For a failure-by-failure recovery reference, see the
[failure and recovery guide](failure-and-recovery.md).
For detached Warrant files and CLI validation, see the
[portable Warrant guide](portable-warrants-and-cli.md).

## Responsibilities at the boundary

| Participant | Supplies or checks | Limit |
| --- | --- | --- |
| Application | The rule, identity and business facts, stable idempotency key, scoped capability, adapter, and verifier | Must route consequential operations through custody; other application paths can bypass this library |
| CAGE facade | Consequence identity, local dispatch reservation, custody invocation, result and Warrant lineage | In-memory guards belong to one `CAGE` instance; no distributed lock or restart restoration |
| Adapter | Applies the selected effect to a named target and reports its observation | An acknowledgement or exception cannot establish the final external Effect |
| Verifier | Independently reads suitable target evidence for this consequence and returns a verification state | A callback can be mistaken or dishonest; CAGE checks its record links, not the truth of its external claims |
| Target system | Stores the business effect and exposes suitable correlation and observation data | Delays or missing evidence can make verification inconclusive |

The caller constructs `CAGE(rule=...)`. A rule returns `EvaluationOutcome`,
including an explicit `DecisionState` and, for a narrowed decision, a
`RequestedEffect` containing the permitted parameters. A returned `ADMITTED`
or `NARROWED` Decision is permission to *attempt* the selected effect through
custody, not a capability or proof of an Effect. The application supplies an
`ExecutionCapability` scoped to the evaluation's `consequence_id`, action
type, and resource ID. Custody checks eligibility and scope before invoking
the adapter. Do not mint an authority merely because a rule admitted an action.

## Writing an adapter

Import `EffectAdapter`, `ExecutionAttempt`, `ExecutionCapability`,
`RequestedEffect`, `AdapterExecutionResult`, and `AdapterExecutionState` from
`cage.adapters`. An adapter implements:

```python
def execute(self, *, execution_attempt, effect, capability) -> AdapterExecutionResult:
    ...
```

The `effect` argument is the effect selected by custody. On a `NARROWED`
Decision it is the permitted effect, which can differ from the action's
original request. Apply exactly that effect. Return an
`AdapterExecutionResult` with a nonblank `result_id`, the same
`execution_attempt`, an `AdapterExecutionState`, and useful receipt
references. `ACKNOWLEDGED`, `REJECTED`, `ERROR`, and `UNKNOWN` are observations;
none proves `BOUND` or `NO_BIND` by itself. Never substitute a new execution
attempt or return a result belonging to a different operation.

Use a target-supported operation or idempotency key when available. CAGE's
local dispatch guard cannot give an external service exactly-once behavior
after process restart or across CAGE instances. Do not infer from a callback
exception that the target was not changed.

The packaged `cage example database.delete` uses
[`SQLiteDeleteAdapter`](../src/cage/_sqlite_example.py); `access.grant` shows
[`SQLiteAccessAdapter`](../src/cage/_access_example.py) receiving a reader
grant after an administrator request was narrowed. These are small reference
implementations, not reusable production adapters.

## Writing a verifier

Import `EffectVerifier`, `EffectVerificationResult`, `VerificationState`, and
`AdapterExecutionResult` from `cage.verifiers`. Implement:

```python
def verify(self, *, adapter_result) -> EffectVerificationResult:
    ...
```

Read target evidence that correlates to the intended consequence, resource,
and selected effect. Return a unique `verification_id`, the exact input
`adapter_result`, the verification state, and observation references. For
`VERIFIED_BOUND` or `VERIFIED_NO_BIND`, provide at least one reference.
Reading a receipt or repeating the adapter's claimed status alone is not
independent verification. A separate vendor is not required: for SQLite, a
separate read connection can observe the same database; for a remote target,
the read must use its authoritative state or operation status.

To claim `VERIFIED_BOUND`, correlate a durable observation to this operation
and the permitted effect. To claim `VERIFIED_NO_BIND`, obtain evidence strong
enough to rule out a delayed completion, including the target's consistency
and operation-status guarantees. An empty read, unavailable receipt, timeout,
or transient error can require `INCONCLUSIVE` instead. CAGE maps these states
to `BOUND`, `NO_BIND`, and `EFFECT_UNKNOWN`, respectively. A verifier must not
mutate the target to make its observation true.

The local payment fixture deliberately writes one ledger entry and returns
adapter `UNKNOWN`. Its first verifier cannot observe the ledger and returns
`INCONCLUSIVE`; a later verifier reads the existing entry and returns
`VERIFIED_BOUND`. Run `cage example payment.release` to see the single
dispatch and linked Warrants. The fixture begins with an empty ledger and
uses one known invoice and amount; production integrations need a durable
operation correlation scheme appropriate to their target.

## Failures, observation, and recovery

Normal Decision, adapter, and verification states are returned as typed
outcomes. Error handling depends on when the failure occurs:

| Situation | What the application can do |
| --- | --- |
| Ineligible Decision or mismatched capability | Correct the input or authority; custody has not invoked the adapter |
| Conflicting idempotency key | Resolve the request identity; do not treat a new key as a safe retry of the old operation |
| Adapter exception, invalid return, or mismatched result | Catch `AdapterInvocationError`, `AdapterContractError`, or `AdapterResultMismatchError`; inspect `error.execution` and verify it without dispatching again |
| Verifier exception or invalid return | Catch the relevant `VerifierInvocationError`, `VerifierContractError`, or `VerificationResultMismatchError`; observe again with `verify(error.execution, ...)` |
| Failed reconciliation | Use `error.previous` and `error.execution` to inspect the prior snapshot and original execution; retry only observation with `reconcile(error.previous, ...)` |
| Assembly failure after a valid verification | `AssuranceAssemblyError` retains `execution`, `verification`, `stage`, and, during reconciliation, `previous` |

If the adapter could have been entered, CAGE consumes its local dispatch
reservation even if it raised. An error's `execution` may contain an SDK
recovery observation with adapter state `UNKNOWN` and origin `SDK_RECOVERY`.
That marker records missing usable adapter output; it is not a receipt from
the target. `verify(error.execution, verifier=...)` performs observation
without another dispatch. A valid but inconclusive first observation returns
an `AssuranceResult`; use `reconcile(previous, verifier=...)` to observe again
and link the new Warrant to the preceding one. Within one facade instance,
one completed first verification and one successor per predecessor are
reserved. Restarting loses those local reservations.

Do not use a parsed portable Warrant to resume execution. `parse_warrant()`
and `load_warrant()` return detached inspection data, not an
`ExecutionResult` or an executable capability. SUMMARY hides specified
business fields and references; FULL can contain sensitive business data.
`validate_warrant()` checks structure and consistency, not authenticity,
current target state, or cryptographic integrity. Keep target credentials out
of references and diagnostics and protect any exported files appropriately.

## Low-level API and compatibility

`cage.core.*` remains available for applications that own the full lifecycle.
`cage.rules`, `cage.adapters`, `cage.verifiers`, `cage.results`, and
`cage.warrants` re-export the supported contracts without copying core
classes. The facade orchestrates the existing custody and verification
functions; it does not replace their Decision/Effect semantics. Existing
v0.6 applications can keep their low-level imports. Adopt the facade and
portable v1 format explicitly; a format-version change, if needed, requires
separate migration guidance.
