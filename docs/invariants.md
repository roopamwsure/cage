# CAGE v0.6 Invariants

These invariants define non-negotiable behavior for the Generic Consequence
Core and the v0.6 Consequence Custody boundary.

For definitions of the core terms used here, see
[Core Terminology](architecture.md#core-terminology).

---

## Invariant 1 — Decision and Effect are independent

A Decision and an Effect describe different parts of the lifecycle.

```text
ADMITTED != BOUND
REFUSED  != NO_BIND
```

A Decision records what CAGE permitted for an evaluation Attempt.

An Effect records what authoritative verification established about the
external business consequence.

One cannot be inferred directly from the other.

---

## Invariant 2 — NO_BIND requires authoritative evidence

`NO_BIND` is a positive assurance claim that the intended Consequence did not
become effective.

None of the following is enough by itself:

- execution was not attempted;
- the adapter rejected the request;
- execution returned an error;
- an API timed out;
- a response was lost;
- an acknowledgement was missing;
- the adapter crashed; or
- transport failed.

CAGE may assert `NO_BIND` only when authoritative verification supports that
conclusion.

---

## Invariant 3 — Uncertainty remains explicit

When CAGE cannot establish whether the Consequence became effective, the Effect
is:

```text
EFFECT_UNKNOWN
```

Uncertainty is preserved rather than converted into either `BOUND` or
`NO_BIND`.

---

## Invariant 4 — Consequence identity is stable

One intended business consequence has one Consequence identity.

That identity survives:

- repeated evaluation;
- replay;
- multiple ExecutionAttempts;
- explicitly supported execution retry;
- reconciliation;
- agent-session changes;
- repeated API calls;
- later verification; and
- later Warrants.

Creating a new Attempt, ExecutionAttempt, verification result, Effect, or
Warrant does not by itself create a new Consequence.

---

## Invariant 5 — Evaluation Attempts are distinct

Each evaluation has its own `Attempt` identity.

Multiple Attempts may refer to the same Consequence.

An Attempt may also reference a previous Attempt to preserve replay lineage.

The Decision belongs to the Attempt that produced it.

---

## Invariant 6 — Replay is re-evaluation only

Replay creates a new evaluation Attempt for an existing Consequence.

It preserves the original Consequence and business intent while allowing the
assurance inputs to be evaluated again.

A replay may therefore produce a different Decision.

Replay does not execute the external operation.

```text
replay != execution retry
replay != reconciliation
```

---

## Invariant 7 — Idempotency is consequence-level safety

Equivalent requests using the same idempotency key resolve to the same
Consequence.

The same key cannot silently represent two materially different business
operations.

If the business intent conflicts with an existing use of the key, CAGE fails
explicitly.

Current business-intent equivalence includes:

- action type;
- Principal identity;
- Resource identity; and
- RequestedEffect.

It does not depend on:

- Action identity;
- proposed Consequence identity;
- Agent identity;
- Attempt identity;
- agent session;
- retry number; or
- replay number.

The idempotency key identifies the intended business operation, not the
incidental mechanics around it.

---

## Invariant 8 — NARROWED executes only the permitted effect

A `NARROWED` Decision carries an explicit `permitted_effect`.

The original RequestedEffect remains preserved for audit and lineage.

Determining whether the permitted effect is actually narrower is domain-specific
and belongs to the supplied evaluation logic.

At custody time, only `permitted_effect` may reach the `EffectAdapter`.

The broader original request must not be executed.

---

## Invariant 9 — Warrant separates DecisionProof from EffectProof

`DecisionProof` and `EffectProof` record different assurance facts.

A valid `DecisionProof` does not establish an `EffectProof`.

A Warrant may legitimately contain a DecisionProof before any EffectProof
exists.

That state is also different from a Warrant containing an EffectProof whose
Effect is `EFFECT_UNKNOWN`.

No EffectProof means no Effect claim has been established yet.

---

## Invariant 10 — Core is domain-neutral

Generic CAGE Core must support different business domains without embedding
their production rules.

Domain-specific logic for areas such as payments, databases, access control,
deployment, or procurement stays outside the Core.

Domain-specific parameters belong in `RequestedEffect.parameters`.

Domain-specific evaluation semantics belong in the supplied evaluation rule.

The same Core should be able to govern materially different Consequence types.

---

## Invariant 11 — Core is vendor-neutral

Generic CAGE Core does not depend on a particular:

- cloud provider;
- AI model;
- agent framework;
- IAM system;
- policy engine;
- policy language; or
- execution provider.

This includes AWS, Azure, GCP, MCP, OpenAI, and Anthropic.

Provider-specific information enters CAGE through normalized inputs or explicit
integration boundaries.

Identity, policy, approval, observability, risk, execution, and cloud-security
platforms remain external systems that CAGE can consume or integrate with.

---

## Invariant 12 — No implicit allow

CAGE does not create permission simply because no failure was detected.

An `ADMITTED` Decision must be returned explicitly by valid supplied evaluation
logic through an `EvaluationOutcome`.

Missing, invalid, incomplete, or untrusted evaluation information must not
default to `ADMITTED`.

Generic Core also does not prescribe one universal set of assurance inputs for
every Consequence.

Those requirements belong to the supplied evaluation logic.

---

## Invariant 13 — Assurance claims are evidence-bounded

CAGE cannot make a stronger assurance claim than the available evidence
supports.

For example:

```text
ADMITTED          != BOUND
REFUSED           != NO_BIND
execution failure != NO_BIND
timeout           != NO_BIND
adapter success   != BOUND
```

If external reality remains unresolved:

```text
EFFECT_UNKNOWN
```

The absence of an EffectProof is not itself an Effect assertion.

---

## Invariant 14 — Execution requires explicit custody

Evaluation never performs an external mutation automatically.

This flow is not allowed:

```text
evaluate_attempt()
    |
    v
ADMITTED
    |
    v
automatic external execution
```

External execution begins only through an explicit custody path.

---

## Invariant 15 — Core remains locally usable

CAGE Core must operate as a local library without requiring CAGE Cloud or
another hosted CAGE service.

Its domain model, evaluation, replay, idempotency, custody, verification, and
proof semantics remain usable without a hosted dependency.

---

## Invariant 16 — Evaluation consumes normalized assurance inputs

Evaluation can consume normalized:

- Evidence;
- Standing;
- Delegation;
- Approval; and
- Context.

These records carry assurance facts and signals into the evaluation process.

They do not become authorization engines, execution mechanisms, or approval
workflows themselves.

The supplied evaluation logic interprets them and returns an explicit
`EvaluationOutcome`.

---

## Invariant 17 — Evaluation is Attempt-scoped

Evaluation happens against an `Attempt`, not directly against an Action alone.

A Decision belongs to the Attempt that produced it.

The same Consequence may therefore receive different Decisions across different
Attempts while preserving one stable Consequence identity.

For example:

```text
Attempt A1 -> ESCALATED
Attempt A2 -> ADMITTED
```

Both Attempts can still refer to the same Consequence.

---

## Invariant 18 — DecisionProof records assurance provenance

A `DecisionProof` records the Decision together with stable references to the
assurance inputs that supported it.

Those references may include:

- Evidence identifiers;
- Standing identifiers;
- Delegation identifiers;
- Approval identifiers; and
- Context identifiers.

The proof explains the basis for the Decision.

It does not establish what became true in the external system.

---

## Invariant 19 — EffectProof requires verification-backed Effect establishment

`EffectProof` records an assurance claim about external reality.

It remains separate from `DecisionProof` and must be backed by an
`EffectVerificationResult`.

CAGE cannot derive an Effect directly from the Decision state.

These shortcuts are invalid:

```text
ADMITTED -> BOUND
REFUSED  -> NO_BIND
```

An `EffectProof` must preserve matching:

- Consequence lineage;
- verification state;
- Effect state; and
- verification references.

The Effect claim is only as strong as the verification that supports it.

---

## Invariant 20 — Evaluation Attempt and ExecutionAttempt are distinct

An evaluation `Attempt` and an `ExecutionAttempt` describe different events.

An evaluation Attempt means:

> one evaluation of a Consequence

An ExecutionAttempt means:

> one identified attempt to carry an eligible Decision into external execution

They have separate identities and must not be treated as interchangeable.

This distinction is what allows replay and execution retry to remain separate
operations.

---

## Invariant 21 — Custody eligibility is explicit

Not every Decision may proceed to execution.

Current custody behavior is:

```text
ADMITTED
    -> original RequestedEffect

NARROWED
    -> Decision.permitted_effect

HELD
ESCALATED
REFUSED
    -> custody ineligible
```

Ineligible Decisions stop before adapter invocation.

Custody therefore carries forward only the execution authority represented by
the Decision.

---

## Invariant 22 — ExecutionCapability is scoped

Execution authority is scoped to the custody operation it is intended to
support.

The current capability binds:

```text
consequence_id
action_type
resource_id
```

A capability for another Consequence, action type, or Resource cannot be reused
for the current execution.

`ExecutionCapability` is not a credential vault.

Provider-specific tokens, secrets, credentials, roles, and permission
documents remain outside the generic Core.

---

## Invariant 23 — EffectAdapter does not determine Effect truth

`EffectAdapter` attempts the external mutation and reports what it observed
about that request.

Its states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These are execution observations, not Effect states.

The following direct mappings are invalid:

```text
ACKNOWLEDGED -> BOUND
REJECTED     -> NO_BIND
ERROR        -> NO_BIND
UNKNOWN      -> EFFECT_UNKNOWN
```

External Effect must be established separately through verification.

---

## Invariant 24 — Custody validates before execution

Before calling the `EffectAdapter`, custody validates:

- Decision eligibility;
- the exact selected effect; and
- `ExecutionCapability` scope.

If any of those checks fail, execution stops before adapter invocation.

The execution boundary is therefore reached only after the relevant custody
conditions have been satisfied.

---

## Invariant 25 — Adapter result lineage must match custody lineage

An adapter returns an `AdapterExecutionResult`.

That result must refer to the expected `ExecutionAttempt`.

A result linked to another execution is a contract error and must fail
explicitly.

Custody does not repair mismatched lineage and does not create an Effect from
the adapter result.

---

## Invariant 26 — Effect claims require authoritative verification

Only an `EffectVerificationResult` can establish the basis for Effect creation.

The mapping is:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

There is no direct conversion from:

```text
AdapterExecutionResult -> Effect
```

Execution observation and authoritative verification remain separate stages.

---

## Invariant 27 — Conclusive verification requires references

`VERIFIED_BOUND` and `VERIFIED_NO_BIND` require verification references.

`INCONCLUSIVE` may have no references.

A conclusive Effect claim therefore carries an explicit verification basis.

---

## Invariant 28 — Reconciliation does not execute

Reconciliation re-checks external reality using an existing
`AdapterExecutionResult`.

It does not:

- invoke an `EffectAdapter`;
- create another external execution;
- create an execution retry; or
- create an evaluation replay.

Therefore:

```text
reconciliation != replay
reconciliation != execution retry
reconciliation != re-execution
```

---

## Invariant 29 — Reconciliation preserves execution lineage

A later reconciliation may create a new:

- `EffectVerificationResult`;
- Effect;
- `EffectProof`; and
- Warrant.

But it preserves the underlying:

- Consequence;
- evaluation lineage;
- `ExecutionAttempt`; and
- `AdapterExecutionResult`.

The new Warrant may link to the earlier one through:

```text
previous_warrant_id
```

Reconciliation adds a new assurance view without creating a new execution.

---

## Invariant 30 — Historical assurance is preserved

Later verification does not rewrite the meaning of earlier assurance records.

For example:

```text
Warrant W1
Effect = EFFECT_UNKNOWN
```

may later be followed by:

```text
Warrant W2
Effect = BOUND
previous_warrant_id = W1
```

`W1` remains a valid record of what CAGE could establish at the earlier point
in time.

`W2` records the later assurance state.

---

## Invariant 31 — CAGE does not become IAM

CAGE may consume normalized identity, delegation, policy, approval, or
execution-authority information.

It does not recreate provider IAM semantics, credential systems, or
authorization platforms inside the generic Core.

Those systems remain external sources or integration points.

---

## Invariant 32 — v0.6 scope remains disciplined

v0.6 establishes the Generic Consequence Core together with Consequence
Custody.

It does not require:

- CAGE Cloud;
- SaaS;
- billing;
- REST APIs;
- database persistence;
- provider-specific production adapters;
- MCP integration;
- provider credential custody;
- general execution-retry orchestration;
- cryptographic Warrant signatures;
- canonical Warrant serialization;
- independent cryptographic Warrant verification;
- HSM or KMS integration;
- post-quantum cryptography;
- AI risk intelligence;
- enterprise deployment;
- a new IAM system;
- a new policy language;
- full consequence graphs; or
- advanced consequence lineage.

Those capabilities belong to later releases, separate product layers, or
integration packages.

---

## Invariant Summary

The v0.6 Core protects six architectural separations:

```text
Decision            != Effect
Evaluation Attempt  != ExecutionAttempt
Replay              != Execution Retry
Adapter Result      != Effect
Execution           != Verification
Reconciliation      != Re-execution
```

Together, these separations define the boundary of Consequence Custody.