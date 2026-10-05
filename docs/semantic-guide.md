# CAGE Decision and Effect Semantics

CAGE separates permission from outcome.

It evaluates a proposed business action, controls whether that action may cross
into external execution, and then records what later verification can establish
about the resulting external state.

Those are different questions:

```text
Decision != Effect
```

A Decision says what CAGE permitted.

An Effect says what authoritative verification established afterward.

This guide explains the states exposed through the v0.7 facade.

For runnable code, start with the [Quickstart](quickstart.md).

For adapter and verifier contracts, see the
[Integration guide](integration-guide.md).

---

## Identity and evaluation

An `Action` describes the proposed operation, including:

- Principal;
- Agent;
- Resource;
- action type; and
- RequestedEffect.

A `Consequence` identifies the intended business consequence.

Each evaluation of that Consequence has its own `Attempt`.

For example:

```text
Consequence C1
    |
    +-- Attempt A1
    +-- Attempt A2
```

Both Attempts can refer to the same business Consequence.

When calling:

```python
CAGE.evaluate(...)
```

the application should supply a stable `idempotency_key` for that business
operation.

Reusing the same key for equivalent business intent resolves to the same
Consequence.

Reusing it for materially different intent fails explicitly.

Passing `previous=...` re-evaluates the same Consequence with a new Attempt and
preserves replay lineage.

It does not invoke an adapter.

---

## Decision

The application rule consumes normalized assurance inputs such as:

```text
Evidence
Standing
Delegation
Approval
Context
```

and returns an `EvaluationOutcome`.

CAGE turns that outcome into a Decision and `DecisionProof`.

`DecisionProof` records the assurance basis for the Decision.

It does not describe what happened in the external system.

The five Decision states are:

| Decision | Meaning |
| --- | --- |
| `ADMITTED` | The original RequestedEffect may proceed toward execution |
| `NARROWED` | Only the explicit `permitted_effect` may proceed |
| `HELD` | Do not execute under custody yet |
| `ESCALATED` | Do not execute under custody; further review or authority is needed |
| `REFUSED` | Do not execute under custody |

These are execution-boundary decisions.

They are not Effect states.

In particular:

```text
ADMITTED != BOUND
REFUSED  != NO_BIND
```

---

## Consequence Custody

For an `ADMITTED` or `NARROWED` Decision, the application may call:

```python
CAGE.execute(...)
```

CAGE then enters Consequence Custody.

Custody checks the selected effect and the supplied `ExecutionCapability`
before invoking the adapter.

For `ADMITTED`:

```text
selected effect = original RequestedEffect
```

For `NARROWED`:

```text
selected effect = Decision.permitted_effect
```

The broader original request must not be substituted back in during execution.

---

## Evaluation Attempt vs ExecutionAttempt

An evaluation `Attempt` and an `ExecutionAttempt` represent different events.

```text
Evaluation Attempt
    -> one evaluation of a Consequence

ExecutionAttempt
    -> one identified attempt to carry an eligible Decision into execution
```

Therefore:

```text
Evaluation Attempt != ExecutionAttempt
```

Replay creates another evaluation Attempt.

It does not create another external execution.

---

## Adapter observation

The adapter attempts the selected external operation.

It may report:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These states describe what the adapter observed about the request.

They do not establish the external Effect.

```text
ACKNOWLEDGED != BOUND
REJECTED     != NO_BIND
ERROR        != NO_BIND
UNKNOWN      != EFFECT_UNKNOWN
```

For example, an acknowledged request may still fail later.

Likewise, a timeout or callback error may occur after the external system has
already applied the operation.

This is why CAGE does not infer Effect from adapter status.

If adapter processing fails after dispatch may have begun, the SDK can preserve
an `UNKNOWN` recovery observation so the application can verify the target
without sending the operation again.

See [Failure and recovery](failure-and-recovery.md).

---

## Verification

Verification examines external evidence after execution.

The application calls:

```python
CAGE.verify(execution, verifier=...)
```

The verifier uses the execution record and its correlation data to inspect the
target.

CAGE checks that the returned verification belongs to the expected lineage.

The verifier remains responsible for the quality and meaning of the external
evidence.

Verification produces:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

These map to Effect states as follows:

| Verification | Effect | Meaning |
| --- | --- | --- |
| `VERIFIED_BOUND` | `BOUND` | Evidence supports that the selected Consequence became effective |
| `VERIFIED_NO_BIND` | `NO_BIND` | Evidence supports that the selected Consequence did not become effective |
| `INCONCLUSIVE` | `EFFECT_UNKNOWN` | The available evidence cannot establish either outcome |

---

## BOUND

`BOUND` means authoritative verification supports the claim that the permitted
Consequence became effective.

It should not be inferred from request submission or acknowledgement alone.

---

## NO_BIND

`NO_BIND` means authoritative verification supports the claim that the
Consequence did not become effective.

The following are not enough by themselves:

```text
adapter rejection
execution error
timeout
missing response
transport failure
no acknowledgement
```

Those conditions may describe a failed or uncertain execution path.

They do not necessarily describe external reality.

---

## EFFECT_UNKNOWN

When verification cannot establish either outcome, CAGE uses:

```text
EFFECT_UNKNOWN
```

This is not an error state.

It is an explicit representation of uncertainty.

For example:

```text
adapter = ACKNOWLEDGED
        |
        v
verification = INCONCLUSIVE
        |
        v
Effect = EFFECT_UNKNOWN
```

CAGE keeps the uncertainty visible until stronger evidence becomes available.

---

## DecisionProof, EffectProof, and Warrant

CAGE keeps Decision provenance and Effect provenance separate.

A Decision-only Warrant may contain:

```text
DecisionProof
EffectProof = absent
```

That means CAGE has an assurance record for the Decision, but no Effect has yet
been established.

This is different from:

```text
DecisionProof
EffectProof(EFFECT_UNKNOWN)
```

In that case, execution and verification have occurred, but the external
outcome remains unresolved.

`EffectProof` connects the Effect to its verification lineage.

A Warrant preserves the assurance state available at that point in time.

Portable JSON Warrants are detached representations of this history.

See [Portable Warrants and CLI](portable-warrants-and-cli.md).

---

## Reconciliation

When a first verification returns:

```text
INCONCLUSIVE
    ->
EFFECT_UNKNOWN
```

the same execution can be observed again later.

Use:

```python
CAGE.reconcile(previous_assurance, verifier=...)
```

Conceptually:

```text
existing execution
    |
    v
Effect = EFFECT_UNKNOWN
    |
    v
later evidence
    |
    v
reconcile()
    |
    v
new verification
    |
    v
new Effect
```

Reconciliation does not invoke the adapter again.

```text
Reconciliation != Re-execution
```

A later Warrant links back to the previous Warrant, preserving the earlier
assurance state.

For a complete example, see the
[Reconciliation walkthrough](reconciliation-walkthrough.md).

---

## Local lifecycle limits

The v0.7 facade keeps dispatch and verification guards in memory.

They apply within one Python process and one `CAGE` instance.

They are not restored automatically after a restart and do not provide a
distributed exactly-once guarantee.

Applications that require durable recovery should maintain their own operation
correlation and use target-system evidence to determine the outcome.

A portable Warrant alone is not enough to resume execution.

When the external outcome is unknown, keep it unknown until suitable
verification resolves it.