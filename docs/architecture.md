# CAGE v0.6 Architecture

## Purpose

CAGE is a vendor-neutral assurance layer at the business-consequence boundary for consequential AI and autonomous-agent actions.

CAGE answers two distinct questions:

1. **Should this proposed autonomous action be allowed to become a real-world business consequence?**
2. **What can CAGE subsequently prove actually became effective in the external system?**

CAGE does not replace:

- agent runtimes;
- IAM or RBAC systems;
- authorization systems;
- policy engines;
- approval systems;
- guardrails;
- workflow systems;
- observability platforms;
- SIEM;
- cloud security controls;
- provider execution platforms.

Those systems may become assurance inputs, adapters, evidence sources, execution systems, or verification systems for CAGE.

The central architectural rule is:

```text
Decision != Effect
```

Identity, evaluation, execution, external observation, verification, and proof are separate concerns and must not be collapsed.

---

## Core Model

The Generic Consequence Core begins with:

```text
Principal
Agent
Resource
RequestedEffect
        |
        v
      Action
        |
        v
   Consequence
        |
        +---- Attempt A1
        +---- Attempt A2
        +---- Attempt A3
```

A `Consequence` represents one intended business consequence.

An `Attempt` represents one evaluation of that Consequence.

Multiple Attempts may refer to the same Consequence.

v0.6 extends that model across external execution and verification:

```text
Action
  |
  v
Consequence
  |
  v
Attempt
  |
  v
Evaluation
  |
  v
Decision
  |
  v
DecisionProof
  |
  v
-----------------------------
     CONSEQUENCE CUSTODY
-----------------------------
  |
  v
ExecutionAttempt
  |
  v
EffectAdapter
  |
  v
External System
  |
  v
AdapterExecutionResult
  |
  v
EffectVerifier
  |
  v
EffectVerificationResult
  |
  v
Effect
  |
  v
EffectProof
  |
  v
Warrant
```

---

## Pre-Effect Assurance Flow

The evaluation path remains:

```text
Action
  |
  v
Consequence
  |
  v
Attempt
  |
  +-- Evidence
  +-- Standing
  +-- Delegation
  +-- Approval
  +-- Context
  |
  v
Deterministic Evaluation Rule
  |
  v
EvaluationOutcome
  |
  v
Decision
  |
  v
DecisionProof
  |
  v
Warrant
```

A Warrant may exist with a `DecisionProof` and no `EffectProof`.

That means CAGE has established and preserved what it decided, but has not yet established what became true in the external system.

---

## Evaluation

Evaluation occurs against an `Attempt`.

The evaluator consumes normalized assurance inputs:

- `Evidence`
- `Standing`
- `Delegation`
- `Approval`
- `Context`

These are passive assurance facts or signals.

They do not themselves implement authorization logic.

The evaluator applies a supplied deterministic evaluation rule and requires an explicit `EvaluationOutcome`.

An `EvaluationOutcome` contains:

- a canonical Decision state;
- an optional `permitted_effect` for `NARROWED`.

Evaluation does not:

- execute an external action;
- create an Effect;
- call a cloud provider;
- implement IAM;
- implement a policy language;
- implement an approval workflow;
- implicitly admit an action when information is missing.

There is no implicit allow.

---

## Decision States

CAGE defines five Decision states:

```text
ADMITTED
HELD
NARROWED
ESCALATED
REFUSED
```

A Decision represents what CAGE permitted for one evaluation Attempt.

A Decision does not establish what became true in the external world.

`NO_BIND` is not a Decision state.

---

## NARROWED Semantics

A `NARROWED` Decision must carry an explicit `permitted_effect`.

The original broader `RequestedEffect` remains preserved on the Action.

Generic Core does not determine whether one effect is more constrained than another. That comparison is domain-specific and belongs to supplied evaluation logic.

Custody must execute only `permitted_effect`.

The original broader requested effect must never reach the EffectAdapter for a `NARROWED` Decision.

---

## Effect States

CAGE defines three Effect states:

```text
BOUND
NO_BIND
EFFECT_UNKNOWN
```

An Effect represents what has been established about the external business consequence.

Decision and Effect are independent dimensions.

For example, all of the following may be valid when supported by authoritative verification:

```text
Decision = ADMITTED
Effect   = BOUND
```

```text
Decision = ADMITTED
Effect   = NO_BIND
```

```text
Decision = ADMITTED
Effect   = EFFECT_UNKNOWN
```

Therefore:

```text
ADMITTED != BOUND
REFUSED  != NO_BIND
```

---

## NO_BIND Semantics

`NO_BIND` may only be asserted when authoritative verification supports the claim that the intended consequence did not become effective.

The following do not, by themselves, prove `NO_BIND`:

- execution was not attempted;
- adapter rejection;
- adapter error;
- timeout;
- lost response;
- missing acknowledgement;
- adapter crash;
- transport failure.

If external reality cannot be established, the correct Effect state is:

```text
EFFECT_UNKNOWN
```

---

## Consequence Identity

A Consequence represents one intended business consequence.

Its identity survives:

- evaluation attempts;
- replay;
- execution attempts;
- execution retries;
- reconciliation;
- agent-session changes;
- repeated API calls;
- later verification;
- later Warrants.

A new evaluation Attempt does not create a new Consequence.

A later verification does not create a new Consequence.

---

## Attempt Identity

Each evaluation attempt has its own `Attempt` identity.

An Attempt contains:

- its own attempt identity;
- the Consequence being evaluated;
- an optional previous Attempt identity.

This supports repeated evaluation while preserving the original Consequence identity.

---

## Replay

Replay means:

```text
re-evaluate the same Consequence
```

Replay creates a new evaluation `Attempt`.

Replay preserves:

- the same Consequence;
- the same original Action;
- the same original RequestedEffect;
- the same consequence-level idempotency identity.

Replay does not execute the external action.

Replay may produce a different Decision when assurance inputs change.

For example:

```text
Consequence C1
    |
    +-- Attempt A1 -> ESCALATED
    |
    +-- Attempt A2 -> ADMITTED
```

Both Decisions still refer to the same intended business consequence.

---

## Consequence-Level Idempotency

Idempotency is enforced at the Consequence level.

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

A reused idempotency key with materially different business intent fails explicitly.

Current business-intent equivalence includes:

- action type;
- principal identity;
- resource identity;
- requested effect.

It deliberately does not depend on:

- action identity;
- proposed consequence identity;
- agent identity;
- attempt identity;
- agent session;
- retry number;
- replay number.

Parameter ordering does not affect consequence equivalence.

Nested requested-effect values are compared semantically.

---

## Assurance Inputs

CAGE Core defines vendor-neutral representations for:

- `Principal`
- `Agent`
- `Resource`
- `Evidence`
- `Standing`
- `Delegation`
- `Approval`
- `Context`

Provider-specific or enterprise-specific information must be normalized before it enters generic evaluation.

For example, results from IAM systems, cloud providers, approval systems, policy engines, or risk systems may become normalized assurance inputs.

CAGE consumes those results rather than recreating those systems.

---

## No Implicit Allow

Generic CAGE Core never creates permission merely because no failure was detected.

Missing or invalid evaluation results do not default to `ADMITTED`.

An `ADMITTED` Decision must be explicitly produced by supplied evaluation logic through a valid `EvaluationOutcome`.

Generic Core does not prescribe which assurance inputs are mandatory for every business consequence.

---

## DecisionProof

A `DecisionProof` records the Decision and stable references to assurance inputs supporting it.

It may reference:

- Evidence;
- Standing;
- Delegation;
- Approval;
- Context.

The proof stores assurance-input identifiers rather than duplicating the assurance objects.

A `DecisionProof` establishes what CAGE decided for an Attempt.

It does not prove that the external consequence became effective.

---

## Consequence Custody

Consequence Custody is the controlled boundary between a CAGE Decision and a real-world external mutation.

Execution must be explicit.

The following is forbidden:

```text
evaluate_attempt()
    |
    v
ADMITTED
    |
    v
automatic execution
```

Instead:

```text
Decision
    |
    v
ExecutionAttempt
    |
    v
execute_under_custody()
```

Custody does not reinterpret evaluation logic.

It carries an already-created Decision across a controlled execution boundary.

---

## Custody Eligibility

`select_effect_for_custody()` defines which Decision states can reach execution.

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

Ineligible Decisions fail before EffectAdapter invocation.

This protects the execution boundary from accidental implicit permission.

---

## ExecutionAttempt Identity

`ExecutionAttempt` is distinct from evaluation `Attempt`.

An evaluation Attempt means:

> one evaluation of a Consequence.

An ExecutionAttempt means:

> one identified attempt to carry an eligible Decision into external execution.

Current lineage includes:

```text
execution_attempt_id
decision
optional previous_execution_attempt_id
```

The Consequence is derived through the Decision lineage.

Therefore:

```text
evaluation Attempt identity != ExecutionAttempt identity
```

Execution retry and evaluation replay are different operations.

---

## ExecutionCapability

`ExecutionCapability` models the structural scope of authority presented to custody.

Current minimal fields are:

```text
capability_id
consequence_id
action_type
resource_id
```

`validate_capability_for_custody()` requires:

```text
same consequence_id
same action_type
same resource_id
```

A capability for another Consequence, action type, or resource cannot be reused.

`ExecutionCapability` does not contain:

- OAuth tokens;
- API keys;
- passwords;
- provider credentials;
- AWS role ARNs;
- Azure tokens;
- IAM policies;
- secrets;
- permission documents.

CAGE models authority scope.

It does not become a credential vault or IAM system.

---

## EffectAdapter

`EffectAdapter` is the vendor-neutral mutation boundary.

Conceptually:

```python
class EffectAdapter(Protocol):
    def execute(
        self,
        *,
        execution_attempt: ExecutionAttempt,
        effect: RequestedEffect,
        capability: ExecutionCapability,
    ) -> AdapterExecutionResult:
        ...
```

The adapter receives:

- the exact ExecutionAttempt;
- the exact selected effect;
- the validated ExecutionCapability.

It does not decide whether the consequence is allowed.

It does not establish Effect truth.

Its responsibility is to attempt external mutation and return a request-level execution observation.

---

## AdapterExecutionResult

The current adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These states describe execution-request observations.

They are not Effect states.

The following mappings are forbidden:

```text
ACKNOWLEDGED != BOUND
REJECTED     != NO_BIND
ERROR        != NO_BIND
UNKNOWN      != EFFECT_UNKNOWN
```

A request-level observation can never substitute for authoritative verification.

---

## Explicit Custody Execution

`execute_under_custody()` orchestrates the execution boundary.

```text
ExecutionAttempt
      |
      v
Decision
      |
      v
select_effect_for_custody()
      |
      v
validate_capability_for_custody()
      |
      v
EffectAdapter.execute(...)
      |
      v
AdapterExecutionResult
```

Current protections include:

- only eligible Decision states can reach the adapter;
- `NARROWED` passes only `permitted_effect`;
- capability mismatch fails before adapter invocation;
- the adapter must return an `AdapterExecutionResult`;
- returned execution lineage must match custody lineage;
- no Effect is created during execution orchestration.

---

## EffectVerifier

Execution and verification are separate responsibilities.

Conceptually:

```python
class EffectVerifier(Protocol):
    def verify(
        self,
        *,
        adapter_result: AdapterExecutionResult,
    ) -> EffectVerificationResult:
        ...
```

Therefore:

```text
EffectAdapter
    -> attempts external mutation

EffectVerifier
    -> determines external reality
```

This separation is foundational.

---

## EffectVerificationResult

Verification states are:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

Conclusive verification states require references.

`INCONCLUSIVE` may have no references.

Effect creation is explicit:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

Only an `EffectVerificationResult` can produce an Effect through:

```text
create_effect_from_verification()
```

There is deliberately no:

```text
AdapterExecutionResult -> Effect
```

shortcut.

---

## Authoritative Verification

CAGE may make an Effect claim only when the available verification basis supports it.

Authoritative verification may eventually be implemented using provider-specific mechanisms, but those mechanisms remain outside generic Core.

Generic Core models:

- verification state;
- verification references;
- verification lineage;
- resulting Effect state.

Examples of possible authoritative sources include:

- system-of-record state;
- authoritative resource state;
- target object existence or absence;
- authoritative transaction state;
- authoritative identity or permission state.

---

## Explicit Uncertainty

When external reality cannot be established:

```text
EFFECT_UNKNOWN
```

is the correct result.

CAGE must preserve uncertainty rather than manufacture certainty.

For example:

```text
AdapterExecutionState = ACKNOWLEDGED
VerificationState     = INCONCLUSIVE
EffectState           = EFFECT_UNKNOWN
```

---

## Reconciliation

Reconciliation re-checks external reality using an existing `AdapterExecutionResult`.

Current flow:

```text
existing AdapterExecutionResult
        |
        v
EffectVerifier
        |
        v
new EffectVerificationResult
```

`reconcile_effect_verification()` has no EffectAdapter parameter.

Therefore:

```text
reconciliation != replay
reconciliation != execution retry
reconciliation != re-execution
```

The same adapter result may be verified again later.

For example:

```text
one external execution
        |
        v
AdapterExecutionResult R1
        |
        +-- Verification V1 = INCONCLUSIVE
        |       |
        |       +-- Effect E1 = EFFECT_UNKNOWN
        |       +-- Warrant W1
        |
        +-- later reconciliation
                |
                +-- Verification V2 = VERIFIED_BOUND
                        |
                        +-- Effect E2 = BOUND
                        +-- Warrant W2
                            previous_warrant_id = W1
```

Reconciliation changes CAGE's knowledge about reality.

It does not cause reality to be executed again.

---

## Replay vs Execution Retry vs Reconciliation

These operations are distinct.

### Replay

```text
re-evaluate the Consequence
```

Creates a new evaluation Attempt.

Does not execute.

### Execution Retry

```text
attempt external execution again
```

Requires a distinct ExecutionAttempt while preserving the same Consequence.

v0.6 provides the identity model needed to distinguish execution retry, but does not introduce a broad retry orchestration feature.

### Reconciliation

```text
verify external reality again
```

Uses an existing AdapterExecutionResult.

Does not automatically execute or re-evaluate.

---

## EffectProof

`EffectProof` is verification-backed.

It contains:

```text
proof_id
effect
verification
```

where `verification` must be an `EffectVerificationResult`.

It validates:

### Same Consequence

```text
Effect.consequence
==
EffectVerificationResult.consequence
```

### Matching state

```text
VERIFIED_BOUND    <-> BOUND
VERIFIED_NO_BIND  <-> NO_BIND
INCONCLUSIVE      <-> EFFECT_UNKNOWN
```

### Matching verification evidence

```text
Effect.verification_refs
==
EffectVerificationResult.references
```

It derives:

```text
verification_id
adapter_result_id
execution_attempt_id
```

An EffectProof cannot be detached from authoritative verification lineage.

---

## Warrant

A CAGE Warrant joins the available assurance proof state for a Consequence.

A minimal Warrant contains:

- warrant identity;
- schema version;
- DecisionProof;
- optional EffectProof;
- optional previous Warrant identity.

A Warrant derives its:

```text
consequence_id
action_id
attempt_id
```

from Decision lineage.

When an EffectProof exists, it also derives:

```text
execution_attempt_id
adapter_result_id
verification_id
```

A Warrant may legitimately exist before an EffectProof exists.

A later Warrant may reference a previous Warrant through:

```text
previous_warrant_id
```

This preserves assurance history without rewriting earlier claims.

A Warrant rejects DecisionProof and EffectProof objects that refer to different Consequences.

---

## Historical Integrity

Later verification must not mutate or erase earlier assurance history.

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

## Evidence-Bounded Assurance

CAGE must never make an assurance claim stronger than the available evidence supports.

Examples:

```text
execution failure != NO_BIND
ADMITTED          != BOUND
REFUSED           != NO_BIND
adapter success   != BOUND
```

Unresolved external state remains:

```text
EFFECT_UNKNOWN
```

Absence of an EffectProof is not treated as an Effect assertion.

---

## Vendor Neutrality

Generic CAGE Core must not depend on:

- AWS;
- Azure;
- GCP;
- MCP;
- OpenAI;
- Anthropic;
- any specific AI model;
- any specific agent runtime;
- any specific policy language;
- any specific IAM platform;
- any specific policy engine;
- any specific execution provider.

External identity, policy, approval, observability, risk, execution, and cloud-security systems remain integrations or inputs rather than capabilities CAGE should recreate.

---

## Domain Neutrality

The same Core must support materially different business consequences.

Examples used in tests include:

```text
database.delete
access.grant
payment.release
```

No database-specific, access-specific, or payment-specific business logic belongs in generic CAGE Core.

Domain-specific parameters belong in `RequestedEffect.parameters` and supplied domain-specific evaluation logic.

---

## Local Operation

CAGE Core must remain usable locally.

Core evaluation, custody contracts, verification contracts, and proof semantics must not depend on CAGE Cloud or any hosted CAGE service.

---

## v0.6 Implemented Boundary

v0.6 includes:

- generic identity and Action contracts;
- Consequence identity;
- evaluation Attempt identity;
- generic assurance inputs;
- deterministic generic evaluation orchestration;
- canonical Decision semantics;
- canonical Effect semantics;
- safe replay;
- consequence-level idempotency;
- DecisionProof;
- ExecutionAttempt identity;
- custody eligibility;
- exact `NARROWED` effect selection;
- scoped ExecutionCapability;
- EffectAdapter;
- AdapterExecutionResult;
- explicit custody execution orchestration;
- EffectVerifier;
- EffectVerificationResult;
- authoritative Effect creation;
- reconciliation;
- verification-backed EffectProof;
- Warrant execution and verification lineage;
- previous-Warrant lineage;
- explicit uncertainty.

v0.6 does not implement:

- CAGE Cloud;
- SaaS;
- billing;
- REST services;
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
- full consequence graphs or advanced consequence lineage.

Those capabilities belong to later releases or integration packages.

---

## v0.6 Architectural Invariants

The implemented v0.6 model protects these invariants:

1. `Decision != Effect`.
2. `ADMITTED` does not automatically execute.
3. Execution requires explicit custody.
4. Replay does not execute.
5. Evaluation Attempt and ExecutionAttempt are different identities.
6. Adapter execution result does not determine Effect.
7. Uncertainty remains explicit.
8. Consequence identity survives evaluation, execution, verification, reconciliation, and proof lineage.
9. `NARROWED` executes only `permitted_effect`.
10. ExecutionCapability is scoped.
11. Effect claims require authoritative verification.
12. `NO_BIND` requires evidence of non-effect.
13. Reconciliation does not execute.
14. CAGE does not become IAM.
15. Generic Core remains vendor-neutral.
16. Historical assurance remains preserved.

---

## Architectural Test

Before adding a new Core abstraction, ask:

> Does this preserve CAGE's ability to control whether a consequential autonomous action may cross into external execution and to prove what actually became effective without collapsing identity, evaluation, execution, verification, or proof?

If the answer is no, the abstraction probably does not belong in generic CAGE Core.
