# Failures and recovery in CAGE v0.7

Start with the [Quickstart](quickstart.md) for a complete local lifecycle.
This guide explains what an application can infer when a callback or SDK
operation fails. It describes the current feature branch behavior, not a
durable recovery protocol.

## First distinguish a state from an exception

| Observation | Meaning | Application action |
| --- | --- | --- |
| Decision `HELD`, `ESCALATED`, or `REFUSED` | No permission for execution | Do not call `execute()` on that evaluation |
| Adapter `UNKNOWN`, `ERROR`, or `REJECTED` | The adapter's observation, not a verified Effect | Verify target evidence; do not infer `NO_BIND` from a status alone |
| Verification `INCONCLUSIVE` / Effect `EFFECT_UNKNOWN` | Verification could not establish either outcome | Keep the returned `AssuranceResult`; use `reconcile()` for a later observation |
| Verification `VERIFIED_BOUND` / Effect `BOUND` | Recorded evidence supports the claimed binding | Keep the Warrant and consider the verifier's target consistency limits |
| Verification `VERIFIED_NO_BIND` / Effect `NO_BIND` | Recorded evidence supports no binding | Only use when the verifier can rule out delayed completion for this operation |

`verify()` and `reconcile()` return an assurance for a valid `INCONCLUSIVE`
outcome. They do not raise merely because the Effect is unknown. Likewise, a
rule may return a refused Decision without raising. A portable Warrant can
describe any of those states; `validate_warrant()` checks the file's structure,
not the accuracy of its claims or the target's current state.

## Errors before an adapter can be called

`CAGETypeError` and `CAGEValueError` identify invalid SDK arguments.
`IdentifierGenerationError` identifies a failing configured ID factory.
The core's custody eligibility and capability-scope errors prevent dispatch
when the Decision or supplied `ExecutionCapability` is unsuitable. An
`IdempotencyConflictError` means the same business key was used for a
different request; resolve the intent rather than making a second key for
the same operation. Check the exception and the original evaluation before
deciding whether any new operation is warranted.

`DuplicateExecutionError` exposes `consequence_id`, the existing
`execution_attempt`, and `execution` when a completed or recoverable result
is available. It can also mean another call is still in progress. It must not
be used as a signal to try a new facade, new key, or new capability to get
around the guard. CAGE reserves dispatch per canonical Consequence within
one facade instance, not across processes or restarts.

## Adapter failure after dispatch may have begun

Once the facade enters the adapter boundary, a Python exception does not
establish that the external system was unchanged. The following SDK errors
retain `error.execution`:

| Error | Immediate interpretation |
| --- | --- |
| `AdapterInvocationError` | The adapter callback raised; the target may have changed |
| `AdapterContractError` | The adapter returned an invalid result after entry |
| `AdapterResultMismatchError` | Its result belongs to a different execution attempt |

For these cases, `error.execution` carries the original evaluation,
capability, and ExecutionAttempt, plus an SDK recovery observation with
adapter state `UNKNOWN` and origin `SDK_RECOVERY`. Its reserved reference
`urn:cage:sdk:recovery-observation` is provenance metadata, not an external
receipt. Keep the original exception cause for operator diagnosis but avoid
logging sensitive provider payloads. For example:

```python
from cage.errors import AdapterInvocationError

try:
    execution = cage.execute(evaluation, adapter=adapter, capability=capability)
except AdapterInvocationError as error:
    execution = error.execution

assurance = cage.verify(execution, verifier=verifier)
```

The same observation step applies to `AdapterContractError` and
`AdapterResultMismatchError`. A verifier without suitable target evidence
should return `INCONCLUSIVE`; it must not manufacture a no-effect claim.
Do **not** call `execute()` again to investigate. The local dispatch
reservation remains consumed after possible adapter entry. Hard process
termination can lose both this reservation and the recovery object.

## Verification failure and later observation

`VerifierInvocationError` means the callback raised;
`VerifierContractError` means it returned an invalid type; and
`VerificationResultMismatchError` means its result points at a different
adapter result. These exceptions retain `execution` and, when raised during
reconciliation, `previous`. No new Effect or Warrant was produced by that
failed call. Correct the verifier or wait for evidence, then observe using
the retained context:

```python
from cage.errors import VerifierInvocationError

try:
    assurance = cage.verify(execution, verifier=verifier)
except VerifierInvocationError as error:
    assurance = cage.verify(error.execution, verifier=working_verifier)
```

After a successful first verification that returns `EFFECT_UNKNOWN`, keep
the returned snapshot and make a later observation without dispatch:

```python
later = cage.reconcile(previous=assurance, verifier=later_verifier)
assert later.warrant.previous_warrant_id == assurance.warrant.warrant_id
```

`reconcile()` is observation-only: it reuses the original adapter result and
creates a new verification, Effect, proof, and Warrant. It does not invoke
the adapter. A reconciliation callback failure retains `error.previous`,
allowing another explicit `reconcile(error.previous, verifier=...)` after the
failure has been addressed. Previously returned snapshots remain historical;
a later observation does not revise them.

An `AssuranceAssemblyError` means the verifier returned a valid observation
but later local assembly failed. It retains `execution`, `verification`,
`stage` (`effect`, `effect_proof`, `warrant`, or `assurance_result`), and any
`previous` snapshot. Inspect the preserved verification before deciding how
to retry observation. Do not describe that failed assembly as a completed
Warrant or discard the observation.

`DuplicateVerificationError` and `DuplicateReconciliationError` expose the
relevant `execution` or `previous` plus `assurance`, which is `None` while a
call is in progress and a completed result after success. They guard one
first verification per execution and one completed successor per predecessor
within the same `CAGE` instance. They do not authorize a second dispatch.

## Portable files and CLI failures

`export_warrant()` raises `WarrantExportError` when a source cannot be safely
represented. `parse_warrant()` raises `WarrantFormatError` for malformed data
and its `UnsupportedWarrantVersionError` subclass for a version the reader
does not support. `load_warrant()` and `dump_warrant()` use `WarrantIOError`
for file access problems. Dump refuses an existing destination unless the
caller explicitly sets `overwrite=True`; it validates before replacing.
Invalid API argument types use `CAGETypeError`. `validate_warrant()` returns
an issue report for malformed record content rather than throwing a format
error. None of these functions reconstructs a runtime capability.

`cage warrant inspect PATH` and `cage warrant validate PATH` exit with `0`
for a structurally valid record, `2` for an invalid command or portable
record, and `1` for file or example failures. Exit `0` does **not** imply
the Effect is `BOUND`. The CLI prints safe error summaries to stderr and
does not display business payloads by default. See the exact format and
omission rules in the [public API](v0.7-public-api.md), sections 18–21.

## Scope of recovery

The facade's idempotency registry and dispatch/verification reservations
live only in one Python process and one `CAGE` instance. A new process does
not inherit them. A portable Warrant is detached inspection data, not an
executable restart context. If a process exits after a possible external
operation, use the application's own durable operation correlation and
target-system evidence to determine the outcome. Do not assume an automatic
retry or an exactly-once guarantee from this SDK.
