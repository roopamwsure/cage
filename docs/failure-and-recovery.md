# Failures and Recovery in CAGE v0.7

Start with the [Quickstart](quickstart.md) for a complete local lifecycle.

This guide explains what an application can safely conclude when an SDK
operation or callback fails.

It describes the current v0.7 behavior. It is not a durable cross-process
recovery protocol.

---

## First distinguish state from failure

Not every non-success state is an exception, and not every exception proves
that the external operation failed.

| Observation | What it means | What the application should do |
| --- | --- | --- |
| Decision `HELD`, `ESCALATED`, or `REFUSED` | Execution was not permitted for that evaluation | Do not call `execute()` for that evaluation |
| Adapter `UNKNOWN`, `ERROR`, or `REJECTED` | An execution observation, not a verified Effect | Verify external evidence; do not infer `NO_BIND` from adapter status alone |
| Verification `INCONCLUSIVE` / Effect `EFFECT_UNKNOWN` | CAGE cannot yet establish the external outcome | Keep the `AssuranceResult` and use `reconcile()` for a later observation |
| Verification `VERIFIED_BOUND` / Effect `BOUND` | Verification evidence supports that the Consequence became effective | Keep the Warrant and account for the verifier's evidence limits |
| Verification `VERIFIED_NO_BIND` / Effect `NO_BIND` | Verification evidence supports that the Consequence did not become effective | Use only when the verifier can rule out delayed completion for that operation |

`verify()` and `reconcile()` return a valid assurance result when verification
is `INCONCLUSIVE`. They do not raise simply because the Effect is
`EFFECT_UNKNOWN`.

Likewise, a rule may return a refused Decision without raising an exception.

A portable Warrant can represent any of these states.
`validate_warrant()` checks the record's structure; it does not prove that the
claims are true or that the external system is still in the same state.

---

## Errors before adapter invocation

Some failures occur before CAGE reaches the external execution boundary.

`CAGETypeError` and `CAGEValueError` indicate invalid SDK arguments.

`IdentifierGenerationError` means a configured ID factory failed.

Custody eligibility and capability-scope failures stop execution when the
Decision or `ExecutionCapability` is not valid for the requested operation.

`IdempotencyConflictError` means the same business key was used for materially
different intent.

That should be treated as an intent conflict, not worked around by inventing a
different key for the same operation.

Review the original evaluation and exception before deciding whether a new
operation is appropriate.

### Duplicate execution

`DuplicateExecutionError` means CAGE has already reserved or used execution for
that canonical Consequence within the current facade instance.

When available, the exception exposes:

```text
consequence_id
execution_attempt
execution
```

It may represent a completed or recoverable execution result, or another call
that is still in progress.

Do not create another facade, idempotency key, or capability simply to bypass
the guard.

The current dispatch reservation is local to one `CAGE` instance and one
Python process. It is not a distributed exactly-once mechanism.

---

## Adapter failure after dispatch may have begun

Once execution enters the adapter boundary, a Python exception does not tell
you whether the external system changed.

The following SDK errors retain `error.execution`:

| Error | Immediate interpretation |
| --- | --- |
| `AdapterInvocationError` | The adapter raised after execution began; the target may have changed |
| `AdapterContractError` | The adapter returned an invalid result after entry |
| `AdapterResultMismatchError` | The returned result belongs to a different ExecutionAttempt |

In these cases, `error.execution` preserves:

- the original evaluation;
- the `ExecutionCapability`;
- the `ExecutionAttempt`; and
- an SDK recovery observation.

The recovery observation uses:

```text
state  = UNKNOWN
origin = SDK_RECOVERY
```

with the reserved reference:

```text
urn:cage:sdk:recovery-observation
```

That reference records SDK recovery provenance. It is not an external receipt.

For example:

```python
from cage.errors import AdapterInvocationError

try:
    execution = cage.execute(
        evaluation,
        adapter=adapter,
        capability=capability,
    )
except AdapterInvocationError as error:
    execution = error.execution

assurance = cage.verify(execution, verifier=verifier)
```

The same recovery pattern applies to `AdapterContractError` and
`AdapterResultMismatchError`.

If the verifier does not have enough evidence to establish the outcome, it
should return `INCONCLUSIVE`.

It must not turn execution ambiguity into `NO_BIND`.

Do not call `execute()` again merely to investigate what happened.

Once adapter entry may have occurred, another dispatch could duplicate the
external operation.

The local dispatch reservation remains consumed after possible adapter entry.

A hard process termination is different: the process may lose both the local
reservation and the recovery object.

---

## Verification failure

Verification errors do not create another execution.

The main verifier failures are:

- `VerifierInvocationError` — the verifier callback raised;
- `VerifierContractError` — the verifier returned an invalid type;
- `VerificationResultMismatchError` — the result refers to the wrong adapter result.

These exceptions retain the `execution` context.

During reconciliation they may also retain `previous`.

No new Effect or Warrant is produced by the failed verification call.

After fixing the verifier or obtaining better evidence, verification can be
attempted again using the retained execution context:

```python
from cage.errors import VerifierInvocationError

try:
    assurance = cage.verify(execution, verifier=verifier)
except VerifierInvocationError as error:
    assurance = cage.verify(
        error.execution,
        verifier=working_verifier,
    )
```

---

## Recovering from EFFECT_UNKNOWN

A successful verification can still return:

```text
INCONCLUSIVE
    ->
EFFECT_UNKNOWN
```

That is a valid assurance state.

Keep the returned snapshot.

When better evidence becomes available, reconcile the same execution rather
than dispatching again:

```python
later = cage.reconcile(
    previous=assurance,
    verifier=later_verifier,
)

assert (
    later.warrant.previous_warrant_id
    == assurance.warrant.warrant_id
)
```

`reconcile()` reuses the original `AdapterExecutionResult`.

It creates a new:

```text
EffectVerificationResult
Effect
EffectProof
Warrant
```

but does not call the adapter.

A reconciliation callback failure retains `error.previous`, so the application
can make another explicit reconciliation attempt after the underlying problem
has been corrected.

Earlier assurance snapshots remain historical records. Later evidence does not
rewrite them.

---

## Assurance assembly failure

`AssuranceAssemblyError` means the verifier returned a valid observation but
CAGE failed while assembling the later assurance objects.

The exception retains:

```text
execution
verification
stage
previous
```

where `stage` may be:

```text
effect
effect_proof
warrant
assurance_result
```

Inspect the retained verification before deciding how to continue.

The failed assembly should not be described as a completed Warrant, but the
verification observation should not be discarded either.

---

## Duplicate verification and reconciliation

`DuplicateVerificationError` and `DuplicateReconciliationError` protect the
local lifecycle from duplicate work.

They expose the relevant `execution` or `previous` object together with an
`assurance` value.

`assurance` is:

```text
None
```

while another call is still in progress, and contains the completed result
after a successful call.

Within one `CAGE` instance, these guards allow:

- one initial verification for an execution; and
- one completed successor for a given reconciliation predecessor.

They do not authorize another external dispatch.

---

## Portable Warrant and CLI failures

Portable Warrant operations use their own error types.

`export_warrant()` raises `WarrantExportError` when the runtime object cannot
be represented safely.

`parse_warrant()` raises:

- `WarrantFormatError` for malformed portable data; or
- `UnsupportedWarrantVersionError` when the format version is unsupported.

`load_warrant()` and `dump_warrant()` use `WarrantIOError` for file-access
problems.

`dump_warrant()` refuses to replace an existing destination unless
`overwrite=True` is supplied, and validates the record before replacement.

Invalid API argument types use `CAGETypeError`.

`validate_warrant()` behaves differently from parsing: it returns an issue
report for invalid record content rather than raising a format exception.

Portable Warrant operations do not reconstruct an `ExecutionCapability` or an
executable runtime context.

### CLI exit codes

The Warrant CLI uses:

```text
0  structurally valid record
1  file or example failure
2  invalid command or invalid portable record
```

For example:

```text
cage warrant inspect PATH
cage warrant validate PATH
```

An exit code of `0` means the portable record is structurally valid.

It does not mean the Effect is `BOUND`.

The CLI writes safe error summaries to stderr and does not print business
payloads by default.

For the full portable format and omission rules, see
[Public API](v0.7-public-api.md), sections 18–21.

---

## Recovery scope

CAGE v0.7 recovery guards are local.

The idempotency registry and dispatch, verification, and reconciliation
reservations live within one Python process and one `CAGE` instance.

A new process does not inherit them.

A portable Warrant is an inspection and assurance artifact. It is not an
executable restart context.

If a process terminates after an external operation may have been sent, the
application must rely on its own durable operation correlation and
target-system evidence to determine what happened.

The SDK does not claim automatic retry or distributed exactly-once execution.