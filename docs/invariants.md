# CAGE v0.6 Invariants

These invariants define non-negotiable behavior for the Generic Consequence Core and the v0.6 Consequence Custody boundary.

## Invariant 1 — Decision and Effect are independent

A Decision does not determine the Effect.

```text
ADMITTED != BOUND
REFUSED  != NO_BIND
```

A Decision records what CAGE permitted for an evaluation Attempt.

An Effect records what authoritative verification established about external reality.

These are different assurance dimensions.

---

## Invariant 2 — NO_BIND requires authoritative evidence

CAGE must not assert `NO_BIND` merely because:

- execution was not attempted;
- an adapter rejected the request;
- execution returned an error;
- an API timed out;
- a response was lost;
- an acknowledgement was missing;
- the adapter crashed;
- transport failed.

`NO_BIND` requires authoritative verification supporting the claim that the intended consequence did not become effective.

---

## Invariant 3 — Uncertainty must remain explicit

If CAGE cannot establish whether a consequence became effective, the Effect must be:

```text
EFFECT_UNKNOWN
```

CAGE must not convert uncertainty into either `BOUND` or `NO_BIND`.

---

## Invariant 4 — Consequence identity is stable

One intended business consequence has one Consequence identity.

The Consequence identity survives:

- repeated evaluation;
- replay;
- execution attempts;
- execution retries;
- reconciliation;
- agent-session changes;
- repeated API calls;
- later verification;
- later Warrants.

A new evaluation Attempt, ExecutionAttempt, verification, Effect, or Warrant does not by itself create a new Consequence.

---

## Invariant 5 — Evaluation Attempts are distinct

Each evaluation attempt has its own `Attempt` identity.

Multiple Attempts may refer to the same Consequence.

An Attempt may reference a previous Attempt identity to preserve replay lineage.

A Decision belongs to the Attempt that produced it.

---

## Invariant 6 — Replay is re-evaluation only

Replay creates a new evaluation Attempt for an existing Consequence.

Replay preserves the original Consequence and business intent.

Replay does not automatically execute the external action.

Replay may produce a different Decision when assurance inputs differ.

Therefore:

```text
replay != execution retry
replay != reconciliation
```

---

## Invariant 7 — Idempotency is consequence-level safety

Equivalent requests using the same idempotency key must resolve to the same Consequence identity.

The same idempotency key must not silently represent two materially different business consequences.

Conflicting business intent associated with the same idempotency key must fail explicitly.

Current business-intent equivalence includes:

- action type;
- principal identity;
- resource identity;
- requested effect.

It deliberately does not depend on:

- action identity;
- proposed consequence identity;
- agent identity;
- Attempt identity;
- agent session;
- retry number;
- replay number.

---

## Invariant 8 — NARROWED carries and executes only an explicit permitted effect

A `NARROWED` Decision must carry an explicit `permitted_effect`.

The original requested effect remains preserved for auditability.

Determining whether one effect is more constrained than another is domain-specific and belongs to supplied evaluation logic.

At custody time, only `permitted_effect` may reach the EffectAdapter.

The broader original requested effect must never be executed for a `NARROWED` Decision.

---

## Invariant 9 — Warrant separates DecisionProof from EffectProof

`DecisionProof` and `EffectProof` are different assurance records.

A valid DecisionProof does not establish an EffectProof.

A Warrant may legitimately contain a DecisionProof while no EffectProof exists yet.

Absence of an EffectProof is different from an EffectProof whose Effect state is `EFFECT_UNKNOWN`.

---

## Invariant 10 — Core is domain-neutral

CAGE Core must not contain production business logic specific to:

- payments;
- databases;
- access control;
- deployment;
- procurement;
- any other single business domain.

Domain-specific parameters belong in generic `RequestedEffect` data.

Domain-specific evaluation semantics belong in supplied evaluation logic.

The same generic Core must support materially different consequence types.

---

## Invariant 11 — Core is vendor-neutral

CAGE Core must not require or embed assumptions about:

- AWS;
- Azure;
- GCP;
- MCP;
- OpenAI;
- Anthropic;
- any specific AI model;
- any specific agent framework;
- any specific IAM system;
- any specific policy engine;
- any specific policy language;
- any specific execution provider.

Provider-specific information must enter CAGE through normalized contracts or external integration boundaries.

External identity, policy, approval, observability, risk, execution, and cloud-security systems provide inputs or integrations rather than capabilities CAGE should recreate.

---

## Invariant 12 — No implicit allow

Missing, invalid, incomplete, or untrusted assurance inputs must never cause CAGE Core to implicitly produce permission.

An `ADMITTED` Decision must be explicitly returned by supplied evaluation logic through a valid `EvaluationOutcome`.

A missing or invalid EvaluationOutcome must fail rather than default to `ADMITTED`.

Generic Core does not prescribe which assurance inputs are mandatory for every consequence.

Those requirements belong to supplied evaluation logic.

---

## Invariant 13 — Assurance claims are evidence-bounded

CAGE must never make an assurance claim stronger than the available evidence supports.

Examples:

```text
ADMITTED          != BOUND
REFUSED           != NO_BIND
execution failure != NO_BIND
timeout           != NO_BIND
adapter success   != BOUND
```

Unresolved external state remains:

```text
EFFECT_UNKNOWN
```

Absence of an EffectProof is not treated as an Effect assertion.

---

## Invariant 14 — Execution requires explicit custody

Evaluation must never automatically execute an external action.

The following flow is forbidden:

```text
evaluate_attempt()
    |
    v
ADMITTED
    |
    v
automatic external execution
```

External mutation may occur only through an explicit custody execution path.

---

## Invariant 15 — The Core must remain locally usable

CAGE Core must operate locally without CAGE Cloud or any hosted CAGE service.

Its domain models, evaluation orchestration, replay semantics, idempotency behavior, custody contracts, verification contracts, and proof semantics must not require a hosted CAGE dependency.

---

## Invariant 16 — Evaluation consumes normalized assurance inputs

Evaluation may consume normalized:

- Evidence;
- Standing;
- Delegation;
- Approval;
- Context.

These objects are passive assurance facts or signals.

They must not themselves become authorization engines, execution mechanisms, or approval workflows.

Supplied evaluation logic interprets them and returns an explicit `EvaluationOutcome`.

---

## Invariant 17 — Evaluation is attempt-scoped

Evaluation occurs against an `Attempt` rather than directly against an Action alone.

A Decision belongs to the Attempt that produced it.

The same Consequence may receive different Decisions across different Attempts while preserving one stable Consequence identity.

For example:

```text
Attempt A1 -> ESCALATED
Attempt A2 -> ADMITTED
```

Both Attempts may still refer to the same Consequence.

---

## Invariant 18 — DecisionProof records assurance provenance

A `DecisionProof` records the Decision together with stable references to assurance inputs supporting that Decision.

Those references may include:

- Evidence identifiers;
- Standing identifiers;
- Delegation identifiers;
- Approval identifiers;
- Context identifiers.

DecisionProof does not establish what became true in the external world.

---

## Invariant 19 — EffectProof requires verification-backed effect establishment

`EffectProof` represents an assertion about external reality.

It must remain independent from DecisionProof.

An EffectProof must be backed by an `EffectVerificationResult`.

CAGE must not manufacture an Effect solely from the Decision state.

In particular:

```text
ADMITTED -> BOUND
REFUSED  -> NO_BIND
```

are forbidden shortcuts.

EffectProof must preserve matching:

- Consequence lineage;
- verification state;
- Effect state;
- verification references.

---

## Invariant 20 — Evaluation Attempt and ExecutionAttempt are distinct

An evaluation `Attempt` and an `ExecutionAttempt` represent different events.

An evaluation Attempt means:

> one evaluation of a Consequence.

An ExecutionAttempt means:

> one identified attempt to carry an eligible Decision into external execution.

They must not share identity semantics or be treated as interchangeable.

---

## Invariant 21 — Custody eligibility is explicit

Custody must not execute every Decision state.

Current eligibility is:

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

Ineligible Decisions must fail before adapter invocation.

---

## Invariant 22 — ExecutionCapability is scoped

Execution authority must be structurally scoped to the intended custody operation.

The current capability scope binds:

```text
consequence_id
action_type
resource_id
```

A capability for another Consequence, action type, or resource must not be reused.

`ExecutionCapability` must not become a credential vault.

Provider-specific tokens, secrets, credentials, role material, and permission documents remain outside generic Core.

---

## Invariant 23 — EffectAdapter does not decide Effect truth

`EffectAdapter` attempts external mutation.

It does not determine whether the external consequence became effective.

Its result is a request-level execution observation only.

The current adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

The following mappings are forbidden:

```text
ACKNOWLEDGED -> BOUND
REJECTED     -> NO_BIND
ERROR        -> NO_BIND
UNKNOWN      -> EFFECT_UNKNOWN
```

---

## Invariant 24 — Custody validates before execution

Before EffectAdapter invocation, custody must validate:

- Decision eligibility;
- exact selected effect;
- ExecutionCapability scope.

A custody validation failure must stop execution before adapter invocation.

---

## Invariant 25 — Adapter result lineage must match custody lineage

An adapter must return an `AdapterExecutionResult`.

The returned result must refer to the expected ExecutionAttempt.

A mismatched result must fail explicitly.

Custody must not create an Effect from an adapter result.

---

## Invariant 26 — Effect claims require authoritative verification

Only an `EffectVerificationResult` may establish the basis for Effect creation.

The verification mapping is:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

There is no direct:

```text
AdapterExecutionResult -> Effect
```

conversion.

---

## Invariant 27 — Conclusive verification requires references

`VERIFIED_BOUND` and `VERIFIED_NO_BIND` require verification references.

`INCONCLUSIVE` may have no references.

A conclusive Effect claim must therefore carry a verification basis.

---

## Invariant 28 — Reconciliation does not execute

Reconciliation re-checks external reality using an existing `AdapterExecutionResult`.

It must not:

- invoke an EffectAdapter;
- create another external execution;
- create an execution retry;
- create an evaluation replay.

Therefore:

```text
reconciliation != replay
reconciliation != execution retry
reconciliation != re-execution
```

---

## Invariant 29 — Reconciliation preserves execution lineage

A later reconciliation may produce a new:

- EffectVerificationResult;
- Effect;
- EffectProof;
- Warrant.

But it must preserve the same underlying:

- Consequence;
- evaluation lineage;
- ExecutionAttempt;
- AdapterExecutionResult.

The later Warrant may reference the earlier Warrant using:

```text
previous_warrant_id
```

---

## Invariant 30 — Historical assurance must not be rewritten

Later verification must not mutate the meaning of earlier assurance artifacts.

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

The earlier uncertainty remains historically valid for the evidence available at that time.

---

## Invariant 31 — CAGE must not become IAM

CAGE may consume normalized identity, policy, delegation, approval, or constrained execution-authority inputs.

It must not recreate provider IAM semantics, credential systems, or authorization platforms inside generic Core.

---

## Invariant 32 — v0.6 scope remains disciplined

v0.6 establishes the Generic Consequence Core plus Consequence Custody semantics.

It does not require:

- CAGE Cloud;
- SaaS;
- billing;
- REST APIs;
- database persistence;
- provider-specific production adapters;
- MCP integration;
- provider credential custody;
- broad execution retry orchestration;
- cryptographic Warrant signatures;
- canonical Warrant serialization;
- independent cryptographic Warrant verification;
- HSM or KMS integration;
- post-quantum cryptography;
- AI risk intelligence;
- enterprise deployment;
- a new IAM system;
- a new policy language;
- full consequence graphs;
- advanced consequence lineage.

Those capabilities belong to later releases or integration packages.

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

These separations are the foundation of Consequence Custody.
