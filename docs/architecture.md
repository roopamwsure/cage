# CAGE v0.6 Architecture

## Purpose

CAGE is a vendor-neutral assurance layer for consequential AI and automated
actions.

It answers two different questions:

1. Should this proposed action be allowed to cross into a real-world business
   consequence?
2. What can CAGE later establish actually became effective in the external
   system?

The central architectural rule is:

```text
Decision != Effect
```

A Decision records what CAGE permitted. An Effect records what authoritative
verification established about external reality.

CAGE does not replace agent runtimes, IAM, authorization systems, policy
engines, approval systems, observability platforms, cloud-security controls,
or execution providers. Those systems can supply assurance inputs, authority,
execution, evidence, or verification around the CAGE lifecycle.

---

## Core Terminology

CAGE uses a small set of terms with specific meanings.

| Term | Meaning |
| --- | --- |
| **Action** | The proposed operation, including the Principal, Agent, Resource, and RequestedEffect. |
| **Consequence** | One intended business consequence whose identity remains stable across evaluation, execution, verification, and reconciliation. |
| **Attempt** | One evaluation of a Consequence. |
| **Decision** | What CAGE permits for a particular evaluation Attempt. |
| **DecisionProof** | The Decision together with stable references to the assurance inputs that supported it. |
| **Consequence Custody** | The controlled boundary that carries an eligible Decision toward external execution. |
| **ExecutionAttempt** | One identified attempt to carry a Decision into external execution. It is distinct from an evaluation Attempt. |
| **ExecutionCapability** | The scoped authority presented to custody for a specific Consequence, action type, and Resource. |
| **EffectAdapter** | The integration that attempts the external mutation and returns an execution observation. |
| **AdapterExecutionResult** | A request-level observation such as `ACKNOWLEDGED`, `REJECTED`, `ERROR`, or `UNKNOWN`. It is not an Effect. |
| **EffectVerifier** | The component that independently examines external reality after execution. |
| **EffectVerificationResult** | The verifier's conclusion: `VERIFIED_BOUND`, `VERIFIED_NO_BIND`, or `INCONCLUSIVE`. |
| **Effect** | What CAGE can establish about the external business consequence: `BOUND`, `NO_BIND`, or `EFFECT_UNKNOWN`. |
| **EffectProof** | The Effect together with the verification lineage and evidence supporting it. |
| **Warrant** | An assurance snapshot that preserves DecisionProof and, when available, EffectProof and predecessor lineage. |
| **Replay** | Re-evaluation of the same Consequence using a new evaluation Attempt. |
| **Execution Retry** | Another external execution attempt for the same Consequence, represented by a new ExecutionAttempt when explicitly supported. |
| **Reconciliation** | Re-verification of an existing execution observation without re-executing the operation. |

The most important separations are:

```text
Decision != Effect
Evaluation Attempt != ExecutionAttempt
Replay != Execution Retry
AdapterExecutionResult != Effect
Execution != Verification
Reconciliation != Re-execution
```

These distinctions are central to the CAGE-2 Consequence Assurance model and
are preserved throughout the Core and SDK.

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

A Consequence is the stable business identity. An Attempt identifies one
evaluation of that Consequence.

v0.6 extends that lineage through external execution and verification:

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

## Pre-effect assurance flow

CAGE intentionally separates the path that grants permission from the path
that establishes external outcome.

Before external execution, the model is:

```text
Action
  -> Consequence
  -> Attempt
  -> Evaluation
  -> Decision
  -> DecisionProof
```

After a Decision becomes eligible for custody, execution and verification add
separate lineage:

```text
Decision
  -> ExecutionAttempt
  -> AdapterExecutionResult
  -> EffectVerificationResult
  -> Effect
  -> EffectProof
  -> Warrant
```

The two paths are connected, but they are not interchangeable.

---

## Evaluation

Evaluation consumes normalized assurance inputs such as:

```text
Evidence
Standing
Delegation
Approval
Context
```

CAGE provides the evaluation structure; the domain supplies the rule.

The generic Core does not define one universal policy language or one universal
set of required inputs. Supplied evaluation logic interprets the inputs and
returns an explicit `EvaluationOutcome`.

There is no implicit allow.

A missing or invalid outcome must not silently become `ADMITTED`.

---

## Decision states

CAGE defines five Decision states:

```text
ADMITTED
HELD
NARROWED
ESCALATED
REFUSED
```

A Decision belongs to the Attempt that produced it.

`ADMITTED` permits the originally requested effect to proceed toward custody.

`NARROWED` permits only an explicit `permitted_effect`.

`HELD`, `ESCALATED`, and `REFUSED` do not permit custody execution.

A Decision says nothing by itself about whether an external Effect exists.

```text
ADMITTED != BOUND
REFUSED  != NO_BIND
```

---

## NARROWED

A `NARROWED` Decision preserves the original RequestedEffect for lineage and
audit while also carrying the smaller `permitted_effect` that may be executed.

Whether one effect is genuinely narrower than another is domain-specific and
belongs to the supplied evaluation rule.

At custody time, only `Decision.permitted_effect` may reach the adapter.

---

## Effect states

CAGE defines three Effect states:

```text
BOUND
NO_BIND
EFFECT_UNKNOWN
```

`BOUND` means authoritative verification supports that the permitted business
Consequence became effective.

`NO_BIND` means authoritative verification supports that the intended
Consequence did not become effective.

`EFFECT_UNKNOWN` means the available evidence cannot establish either outcome.

`NO_BIND` is a positive assurance claim. It must not be inferred simply from a
rejection, timeout, error, lost response, or absence of acknowledgement.

---

## Consequence identity

A Consequence identifies one intended business operation.

That identity survives:

- replay;
- multiple evaluation Attempts;
- distinct ExecutionAttempts, including any explicitly supported execution
  retry;
- verification;
- reconciliation;
- later Effects;
- later EffectProofs; and
- later Warrants.

A new lifecycle event does not by itself create a new business Consequence.

---

## Attempt identity

An evaluation `Attempt` identifies one evaluation of a Consequence.

Replay creates a new Attempt while preserving the same Consequence and business
intent.

A Decision belongs to the Attempt that produced it.

An Attempt may refer to a previous Attempt to preserve replay lineage.

---

## Replay

Replay means:

```text
re-evaluate the Consequence
```

It creates a new evaluation Attempt.

Replay does not execute an external operation.

A replay may produce a different Decision when assurance inputs have changed.

```text
Replay != Execution Retry
Replay != Reconciliation
```

---

## Consequence-level idempotency

CAGE treats idempotency as business-consequence safety rather than merely
transport retry handling.

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

The same key with materially different business intent must fail explicitly.

Current business-intent equivalence includes:

- action type;
- Principal identity;
- Resource identity; and
- RequestedEffect.

It does not depend on incidental identifiers such as Attempt identity, Agent
identity, retry counters, replay counters, or a proposed replacement
Consequence ID.

---

## Assurance inputs

Normalized Evidence, Standing, Delegation, Approval, and Context records carry
facts into evaluation.

They are not themselves policy engines, authorization systems, approval
workflows, or execution mechanisms.

Supplied evaluation logic decides what those inputs mean for the current
Consequence.

---

## DecisionProof

`DecisionProof` records the Decision together with stable references to the
assurance inputs that supported it.

It preserves Decision provenance.

It does not establish what became true in the external system.

---

## Consequence Custody

Consequence Custody is the controlled boundary between an eligible Decision and
external mutation.

Custody begins after CAGE has produced a Decision. It works with the existing
Decision and Consequence lineage rather than recreating evaluation logic.

A Decision may make a Consequence eligible for custody, but it cannot be turned
directly into an Effect.

```text
ADMITTED != BOUND
```

The custody boundary carries permission toward execution while preserving the
separate path needed to establish external outcome.

---

## Custody eligibility

`select_effect_for_custody()` follows this behavior:

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

An ineligible Decision must fail before adapter invocation.

For `NARROWED`, the broader original request must never reach the adapter.

---

## ExecutionAttempt

An `ExecutionAttempt` identifies one attempt to carry an eligible Decision into
external execution.

It is separate from the evaluation Attempt.

Current lineage includes:

```text
execution_attempt_id
decision
optional previous_execution_attempt_id
```

The Consequence is reached through the Decision lineage.

```text
Evaluation Attempt != ExecutionAttempt
```

v0.6 defines the identity needed to distinguish future execution retry from
replay, but it does not introduce general retry orchestration.

---

## ExecutionCapability

`ExecutionCapability` models the scope of execution authority relevant to the
Consequence.

Current fields are:

```text
capability_id
consequence_id
action_type
resource_id
```

Custody requires the capability to match the current:

```text
consequence_id
action_type
resource_id
```

A capability for a different Consequence, action type, or Resource cannot be
reused.

`ExecutionCapability` is not a credential container. OAuth tokens, API keys,
passwords, cloud credentials, roles, IAM policies, secrets, and permission
documents remain outside the generic Core.

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

The adapter receives the exact ExecutionAttempt, the effect selected by
custody, and the validated ExecutionCapability.

It attempts the external mutation and returns a request-level observation.

It does not decide whether execution is allowed and does not determine Effect
truth.

---

## AdapterExecutionResult

The adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These describe what was observed about the request.

They do not establish the business Effect.

```text
ACKNOWLEDGED != BOUND
REJECTED     != NO_BIND
ERROR        != NO_BIND
UNKNOWN      != EFFECT_UNKNOWN
```

The adapter result is therefore an execution observation, not an assurance
claim about final external state.

---

## Explicit custody execution

Execution begins only through an explicit custody path.

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

The path enforces Decision eligibility, exact effect selection, capability
scope, adapter-result type, and expected execution lineage.

No Effect is created during custody execution.

---

## EffectVerifier

External-state verification is separate from execution.

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

The roles are different:

```text
EffectAdapter
    -> attempts external mutation

EffectVerifier
    -> examines what became true afterward
```

The same component may implement both roles in a particular integration, but
the semantic responsibilities remain separate.

---

## EffectVerificationResult

Verification produces:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

The two conclusive states require verification references.

`INCONCLUSIVE` may have no references.

Effect creation follows this mapping:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

Only an `EffectVerificationResult` provides the basis for authoritative Effect
creation.

There is no direct:

```text
AdapterExecutionResult -> Effect
```

shortcut.

---

## Authoritative verification

Authoritative verification is the step that supports a CAGE Effect claim.

The verifier must use evidence suitable for the target and operation being
checked. CAGE can validate record consistency and lineage, but the integration
is responsible for the quality of the external evidence.

`BOUND` must not be inferred merely from command submission, API
acknowledgement, transport success, or lack of errors.

`NO_BIND` must not be inferred merely from failure, timeout, rejection,
missing response, or a crashed adapter.

When neither claim can be supported, the correct state is `EFFECT_UNKNOWN`.

---

## Explicit uncertainty

CAGE keeps unresolved external state explicit.

```text
execution request sent
        |
        v
adapter observation = ACKNOWLEDGED
        |
        v
authoritative verification = INCONCLUSIVE
        |
        v
EFFECT_UNKNOWN
```

The model does not manufacture `BOUND` or `NO_BIND` when evidence is
insufficient.

---

## Reconciliation

Reconciliation re-checks external reality for an execution that has already
occurred.

```text
existing AdapterExecutionResult
        |
        v
EffectVerifier
        |
        v
new EffectVerificationResult
```

It uses the existing AdapterExecutionResult and does not invoke an
EffectAdapter.

```text
Reconciliation != Replay
Reconciliation != Execution Retry
Reconciliation != Re-execution
```

For example:

```text
one external execution
        |
        v
AdapterExecutionResult R1
        |
        v
Verification V1 = INCONCLUSIVE
        |
        v
Effect E1 = EFFECT_UNKNOWN
        |
        v
Warrant W1
        |
        v
later reconciliation
        |
        v
Verification V2 = VERIFIED_BOUND
        |
        v
Effect E2 = BOUND
        |
        v
Warrant W2
        previous_warrant_id = W1
```

The external execution happened once. What changed later was CAGE's evidence
about that execution.

---

## Replay, Execution Retry, and Reconciliation

These operations address different lifecycle events.

```text
Replay
    -> new evaluation Attempt

Execution Retry
    -> new ExecutionAttempt

Reconciliation
    -> new observation of an existing execution
```

v0.6 defines enough identity to keep them distinct. General execution-retry
orchestration remains outside the release.

---

## EffectProof

`EffectProof` binds an Effect to the verification that supports it.

It contains:

```text
proof_id
effect
verification
```

The proof requires matching Consequence lineage, matching verification and
Effect state, and matching verification references.

```text
VERIFIED_BOUND    <-> BOUND
VERIFIED_NO_BIND  <-> NO_BIND
INCONCLUSIVE      <-> EFFECT_UNKNOWN
```

It also derives:

```text
verification_id
adapter_result_id
execution_attempt_id
```

This keeps Effect claims tied to the evidence and execution lineage that
justify them.

---

## Warrant

A Warrant preserves an assurance snapshot for a Consequence.

A decision-only Warrant is valid:

```text
DecisionProof
EffectProof = absent
```

That is different from a Warrant whose EffectProof contains
`EFFECT_UNKNOWN`.

When EffectProof exists, the Warrant carries execution and verification
lineage. A later Warrant may reference an earlier Warrant using
`previous_warrant_id`.

Historical Warrants are not rewritten when new evidence appears.

---

## Historical integrity

Earlier uncertainty remains valid for the evidence available at that time.

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

The later Warrant adds a new assurance state. It does not erase or rewrite the
earlier one.

---

## Evidence-bounded assurance

CAGE does not make assurance claims stronger than the available evidence.

Examples:

```text
ADMITTED          != BOUND
REFUSED           != NO_BIND
adapter success   != BOUND
execution failure != NO_BIND
timeout           != NO_BIND
```

When external state remains unresolved, it stays `EFFECT_UNKNOWN`.

---

## Vendor neutrality

Generic Core does not depend on a specific cloud provider, model vendor, agent
runtime, IAM system, policy engine, policy language, or execution provider.

Provider-specific information enters through normalized contracts and explicit
integration boundaries.

---

## Domain neutrality

Generic Core does not hardcode production business logic for one domain.

Domain-specific parameters belong in RequestedEffect data, and domain-specific
assurance semantics belong in supplied evaluation logic.

The same Core can support materially different Consequence types.

---

## Local operation

CAGE Core remains usable locally without CAGE Cloud or another hosted CAGE
service.

The core domain model, evaluation, replay, idempotency, custody, verification,
and proof semantics do not depend on a hosted control plane.

---

## v0.6 implemented boundary

v0.6 established:

- the Generic Consequence Core;
- stable Consequence identity;
- evaluation Attempts and replay;
- normalized assurance inputs;
- Decision and Effect semantics;
- consequence-level idempotency;
- DecisionProof and EffectProof;
- Consequence Custody;
- ExecutionAttempt identity;
- scoped ExecutionCapability;
- EffectAdapter and AdapterExecutionResult;
- authoritative verification;
- explicit `EFFECT_UNKNOWN`;
- reconciliation without re-execution; and
- Warrant execution, verification, and predecessor lineage.

It did not introduce a hosted control plane, provider-specific production
suites, general execution-retry orchestration, cryptographic Warrant signing,
or enterprise deployment infrastructure.

---

## v0.6 architectural invariants

The v0.6 architecture depends on these non-negotiable rules:

1. `Decision != Effect`.
2. `ADMITTED` does not automatically execute.
3. Execution requires explicit Consequence Custody.
4. Replay does not execute.
5. Evaluation Attempt and ExecutionAttempt are distinct.
6. AdapterExecutionResult does not determine Effect.
7. Uncertainty remains explicit as `EFFECT_UNKNOWN`.
8. Consequence identity survives custody.
9. `NARROWED` executes only `permitted_effect`.
10. ExecutionCapability remains scoped to the intended operation.
11. Effect claims require authoritative verification.
12. `NO_BIND` requires evidence of non-effect.
13. Reconciliation does not execute.
14. Custody does not become IAM.
15. Generic Core remains vendor-neutral.
16. Historical assurance remains preserved.

See [Core invariants](invariants.md) for the full invariant set.

---

## Architectural test

Before adding a new Core abstraction, ask:

> Does this help CAGE decide whether a consequential action may cross into
> external execution, or help establish what actually became effective while
> preserving identity, evidence, and lineage?

If the answer is no, the abstraction probably belongs outside the generic Core.
