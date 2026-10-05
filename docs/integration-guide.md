# Integrating CAGE v0.7

This guide covers the application-facing boundaries around CAGE: evaluation
rules, adapters, verifiers, recovery behavior, and trust assumptions.

For a runnable local example, start with the
[Quickstart](quickstart.md).

For exact signatures and import paths, see the
[Public API](v0.7-public-api.md).

The examples in this repository use disposable fixtures. They demonstrate the
integration model; they are not production payment, access-control, or database
integrations.

For related guidance:

- [Failure and recovery](failure-and-recovery.md)
- [Portable Warrants and CLI](portable-warrants-and-cli.md)
- [Decision and Effect semantics](semantic-guide.md)

---

## Who is responsible for what?

CAGE sits between application intent and external execution, but it does not
own every part of that path.

| Participant | Responsibility | Important limit |
| --- | --- | --- |
| Application | Supplies the evaluation rule, identities, business facts, stable idempotency key, scoped capability, adapter, and verifier | Other application paths can still bypass CAGE unless the application routes consequential operations through custody |
| CAGE facade | Preserves Consequence identity, manages local lifecycle guards, invokes custody and verification, and assembles lineage and Warrants | Current guards are in-memory and belong to one `CAGE` instance |
| Adapter | Applies the selected effect to the target and reports what it observed | Its acknowledgement or failure does not establish the final Effect |
| Verifier | Reads suitable external evidence and reports what can be established | CAGE validates lineage and structure; it cannot prove that a dishonest or faulty verifier told the truth |
| Target system | Holds the external business state and exposes evidence that can be correlated to the operation | Delays, weak consistency, or missing evidence may leave the Effect unresolved |

A typical application creates:

```python
cage = CAGE(rule=rule)
```

The rule returns an `EvaluationOutcome`.

For a `NARROWED` Decision, that outcome also carries the permitted
`RequestedEffect`.

An `ADMITTED` or `NARROWED` Decision gives CAGE permission to move toward
execution.

It is not itself an execution capability and it is not proof of an Effect.

The application separately supplies an `ExecutionCapability` scoped to:

```text
consequence_id
action_type
resource_id
```

Custody validates that scope before invoking the adapter.

An application should not manufacture execution authority merely because the
evaluation returned `ADMITTED`.

---

## Writing an adapter

Import the adapter contracts from `cage.adapters`.

An adapter implements:

```python
def execute(
    self,
    *,
    execution_attempt,
    effect,
    capability,
) -> AdapterExecutionResult:
    ...
```

The adapter receives:

- the current `ExecutionAttempt`;
- the effect selected by custody; and
- the validated `ExecutionCapability`.

The `effect` argument is important.

For an `ADMITTED` Decision, it is the original requested effect.

For a `NARROWED` Decision, it is the permitted effect.

The adapter should apply exactly the effect it receives rather than returning
to the original Action and reconstructing the request independently.

A successful return is an `AdapterExecutionResult` containing:

- a nonblank `result_id`;
- the same `ExecutionAttempt`;
- an `AdapterExecutionState`; and
- any useful receipt or correlation references.

The adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These describe the execution request.

They do not establish:

```text
BOUND
NO_BIND
EFFECT_UNKNOWN
```

The adapter also must not substitute another ExecutionAttempt or return a
result belonging to a different operation.

### External idempotency

When the target supports its own operation ID or idempotency mechanism, use
it.

CAGE's local dispatch guard protects the lifecycle within a single facade
instance. It cannot guarantee exactly-once behavior across process restarts,
multiple application instances, or an external service.

This distinction matters most when the adapter raises after the request may
already have reached the target.

A callback exception does not prove the external operation failed.

---

## Reference adapters

The repository includes small local examples.

`cage example database.delete` uses
[`SQLiteDeleteAdapter`](../src/cage/_sqlite_example.py).

The `access.grant` example uses
[`SQLiteAccessAdapter`](../src/cage/_access_example.py) and demonstrates a
reader grant being executed after a broader administrator request was
narrowed.

These implementations are examples of the contract, not production adapters.

---

## Writing a verifier

Import the verification contracts from `cage.verifiers`.

A verifier implements:

```python
def verify(
    self,
    *,
    adapter_result,
) -> EffectVerificationResult:
    ...
```

Its job is to examine external evidence for the operation represented by the
`AdapterExecutionResult`.

A verifier should correlate that evidence to the intended:

- Consequence;
- Resource;
- selected effect; and
- external operation or receipt, where the target provides one.

It returns:

- a unique `verification_id`;
- the exact input `adapter_result`;
- a `VerificationState`; and
- observation references.

The verification states are:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

`VERIFIED_BOUND` and `VERIFIED_NO_BIND` require at least one verification
reference.

---

## What counts as independent verification?

Independent verification does not necessarily mean a different vendor or
service.

It means the Effect is established from external state or operation evidence
rather than simply repeating the adapter's own conclusion.

For SQLite, that can be a separate read of the same database.

For a remote API, it may be a target-side operation-status endpoint or an
authoritative read of the resource.

A receipt can be useful evidence, but merely rereading:

```text
adapter said ACKNOWLEDGED
```

is not independent verification of the business Effect.

---

## Establishing BOUND

Return `VERIFIED_BOUND` only when the observed evidence supports the claim
that the permitted Consequence became effective.

Ideally, the verifier can correlate:

```text
this Consequence
+
this external operation
+
this selected effect
+
this target state
```

The strength of the verification depends on what the target system exposes.

CAGE preserves the result and its references, but the verifier is responsible
for interpreting the target correctly.

---

## Establishing NO_BIND

`VERIFIED_NO_BIND` requires stronger evidence than an error or empty response.

The verifier should be able to rule out the intended Consequence becoming
effective, including any relevant delayed-completion behavior of the target.

For example, these observations may be insufficient by themselves:

```text
request timed out
receipt unavailable
initial read returned nothing
temporary target error
```

If the available evidence cannot establish either outcome, return:

```text
INCONCLUSIVE
```

CAGE will represent the Effect as:

```text
EFFECT_UNKNOWN
```

A verifier should never mutate the target in order to make its observation
true.

---

## Reconciliation

Reconciliation is useful when the first verification cannot establish the
Effect.

The flow is:

```text
existing execution
    |
    v
first verification = INCONCLUSIVE
    |
    v
Effect = EFFECT_UNKNOWN
    |
    v
later evidence becomes available
    |
    v
reconcile()
    |
    v
new verification
```

The important point is that reconciliation does not invoke the adapter again.

It observes the same execution.

The local payment example demonstrates this behavior.

The fixture performs one external write and returns adapter state `UNKNOWN`.

The first verifier cannot observe the ledger and returns `INCONCLUSIVE`.

A later verifier reads the existing ledger entry and returns
`VERIFIED_BOUND`.

Run:

```text
cage example payment.release
```

to see the single dispatch and linked Warrants.

Production integrations should use a durable correlation mechanism appropriate
to the target rather than relying on the fixture's in-memory assumptions.

---

## Failure and recovery

Normal Decision, adapter, and verification states are returned as typed
results.

Exceptions represent failures in SDK usage, callback execution, contract
validation, or local assembly.

The recovery action depends on where the failure happened.

| Situation | Recommended response |
| --- | --- |
| Ineligible Decision or capability mismatch | Correct the input or authority; the adapter has not been invoked |
| Idempotency conflict | Resolve the business intent rather than treating a new key as a safe retry |
| Adapter exception or invalid adapter result | Inspect `error.execution` and verify the preserved execution without dispatching again |
| Verifier exception or invalid verification result | Use the retained execution context and observe again with a corrected verifier |
| Reconciliation failure | Use the retained `previous` snapshot and retry observation only |
| Assurance assembly failure | Inspect the retained verification and assembly stage before deciding how to proceed |

If adapter entry may have occurred, CAGE consumes the local dispatch
reservation even when the callback raises.

The retained execution may contain a recovery observation with:

```text
state  = UNKNOWN
origin = SDK_RECOVERY
```

That marker means the SDK lacks a usable adapter result.

It is not an external receipt.

Use:

```python
cage.verify(error.execution, verifier=...)
```

to investigate without causing another dispatch.

For the complete failure matrix, see
[Failure and recovery](failure-and-recovery.md).

---

## Trust boundaries

CAGE can validate its own contracts and lineage.

It cannot independently prove that every external input is truthful.

For example:

- an application can supply incorrect identity or business facts;
- an adapter can misreport what the target returned;
- a verifier can implement weak or incorrect verification logic;
- a target can expose stale or eventually consistent state.

CAGE therefore treats trust boundaries explicitly.

The SDK can verify that an `EffectVerificationResult` belongs to the expected
adapter result and that proof lineage is internally consistent.

It cannot determine whether the verifier's external observation was honest or
whether the target's evidence was authoritative enough for the application's
risk model.

That judgment belongs to the integration.

---

## Portable Warrants are not restart state

A parsed portable Warrant is detached assurance data.

It is not:

```text
ExecutionResult
ExecutionCapability
live facade state
restart context
```

Do not use a portable Warrant to resume or reconstruct execution.

`SUMMARY` disclosure omits selected business fields and references.

`FULL` disclosure can contain sensitive business data.

`validate_warrant()` checks structural and semantic consistency of the portable
record.

It does not establish:

- authenticity;
- cryptographic integrity;
- current external state; or
- truth of the verifier's claims.

Keep secrets and provider credentials out of Warrant references and
diagnostics.

Protect exported Warrant files according to the sensitivity of the information
they contain.

---

## Local lifecycle limits

The current facade keeps its idempotency registry and dispatch, verification,
and reconciliation reservations in memory.

Those guards apply to:

```text
one Python process
+
one CAGE instance
```

They are not distributed locks.

A process restart does not restore them automatically.

Applications that need durable recovery should maintain their own durable
operation correlation and use target-side evidence to determine what happened
after an interruption.

CAGE v0.7 does not claim distributed exactly-once execution.

---

## Low-level API and compatibility

Applications that already own the full lifecycle can continue using
`cage.core.*`.

The following modules expose supported contracts for developer-facing use:

```text
cage.rules
cage.adapters
cage.verifiers
cage.results
cage.warrants
```

These modules re-export the existing Core contracts rather than defining
parallel models.

The `CAGE` facade orchestrates the existing evaluation, custody, verification,
reconciliation, and Warrant behavior.

It does not replace the underlying Decision or Effect semantics.

Existing v0.6 applications can continue using the low-level API.

Adoption of the facade and portable Warrant format is explicit rather than
required for compatibility.

Any future portable-format version change should include separate migration
guidance.