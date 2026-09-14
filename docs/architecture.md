# CAGE v0.5 Architecture

## Purpose

CAGE is a vendor-neutral consequence-assurance layer for consequential actions taken by AI agents and autonomous systems.

CAGE does not replace agent runtimes, IAM, authorization systems, policy engines, approval systems, guardrails, observability, or cloud security controls.

Those systems may provide normalized assurance inputs to CAGE.

CAGE operates at the business consequence boundary.

Its purpose is to determine, preserve, verify, and prove the assurance status of an intended business consequence without recreating the systems that authorize, execute, or observe the underlying operation.

## Core Model

The Generic Consequence Core is organized around the following concepts:

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
        +---- Attempt 1
        +---- Attempt 2
        +---- Attempt 3
```

A Consequence represents one intended business consequence.

An Attempt represents one evaluation of that Consequence.

Multiple Attempts may refer to the same Consequence.

## Pre-Effect Assurance Flow

The v0.5 evaluation path is:

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

A Warrant may exist with a DecisionProof and no EffectProof.

This means that CAGE has established and preserved the decision assurance record but has not yet established what became true in the external system.

## Evaluation

Evaluation occurs against an Attempt.

The evaluator consumes already-normalized assurance inputs:

* Evidence
* Standing
* Delegation
* Approval
* Context

These inputs are passive assurance facts or signals.

They do not themselves implement authorization logic.

The evaluator applies a supplied deterministic evaluation rule and requires that rule to return an explicit EvaluationOutcome.

An EvaluationOutcome contains:

* a canonical Decision state
* an optional permitted effect for NARROWED outcomes

The evaluator then constructs the canonical CAGE Decision.

Evaluation does not:

* execute the external action
* create an Effect
* call a cloud provider
* implement IAM
* implement a policy language
* implement an approval workflow
* implicitly admit an action when information is missing

A rule that fails to return a valid EvaluationOutcome does not result in an implicit ADMITTED Decision.

## Decision States

CAGE defines five Decision states:

* ADMITTED
* HELD
* NARROWED
* ESCALATED
* REFUSED

NO_BIND is not a Decision state.

A Decision represents what CAGE permitted for a specific Attempt.

A Decision does not establish what became true in the external world.

## NARROWED Semantics

A NARROWED Decision must carry an explicit permitted effect.

The originally requested effect remains preserved on the Action.

The permitted effect represents the constrained effect selected by the supplied evaluation logic.

Determining whether one effect is more constrained than another is domain-specific and belongs to the supplied evaluation logic rather than generic CAGE Core.

## Effect States

CAGE defines three Effect states:

* BOUND
* NO_BIND
* EFFECT_UNKNOWN

An Effect represents what has been established about the external business consequence.

Decision and Effect are independent dimensions.

For example:

```text
Decision = ADMITTED
Effect   = BOUND
```

is valid.

```text
Decision = ADMITTED
Effect   = NO_BIND
```

is also valid when authoritative verification establishes that the consequence did not become effective.

```text
Decision = ADMITTED
Effect   = EFFECT_UNKNOWN
```

is valid when external reality cannot yet be established.

ADMITTED does not imply BOUND.

REFUSED does not imply NO_BIND.

## NO_BIND Semantics

NO_BIND may only be asserted when there are adequate grounds to establish that the intended consequence did not become effective.

The following do not, by themselves, prove NO_BIND:

* execution was not attempted
* execution returned an error
* an API timed out
* a response was lost
* the agent received no confirmation

If external reality cannot be established, the correct Effect state is EFFECT_UNKNOWN.

## Consequence Identity

A Consequence represents one intended business consequence.

Its identity survives:

* evaluation attempts
* retries
* replay
* agent-session changes
* repeated API calls

Multiple Attempts may refer to the same Consequence.

A new Attempt does not, by itself, create a new Consequence.

## Attempt Identity

Each evaluation attempt has its own Attempt identity.

An Attempt contains:

* its own attempt identity
* the Consequence being evaluated
* an optional previous Attempt identity

This allows repeated evaluation while preserving the identity of the original business consequence.

## Replay

Replay means re-evaluating an existing Consequence using a new Attempt.

Replay preserves:

* the same Consequence
* the same original Action
* the same original RequestedEffect
* the same idempotency identity

Replay creates:

* a new Attempt identity
* linkage to the previous Attempt

Replay does not automatically execute the external action again.

Replay may produce a different Decision when assurance inputs have changed.

For example:

```text
Consequence C1
    |
    +-- Attempt A1
    |      -> ESCALATED
    |
    +-- Attempt A2
           -> ADMITTED
```

Both Decisions still refer to the same intended business consequence.

## Consequence-Level Idempotency

Idempotency is enforced at the Consequence level.

For v0.5:

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

A reused idempotency key with materially different consequence semantics must fail explicitly.

For v0.5, consequence equivalence compares:

* action type
* principal identity
* resource identity
* requested effect

The following identities do not, by themselves, create a new Consequence:

* action identity
* consequence identity proposed by a retry
* agent identity
* attempt identity
* agent session
* retry number
* replay number

Parameter ordering does not affect consequence equivalence.

Nested requested-effect values are compared semantically.

This is a v0.5 contract and may be refined before the stable v1.0 Consequence specification.

## Assurance Inputs

CAGE Core defines vendor-neutral representations for:

* Principal
* Agent
* Resource
* Evidence
* Standing
* Delegation
* Approval
* Context

Provider-specific or enterprise-specific information must be normalized into these contracts before it enters generic evaluation.

For example, decisions or signals from IAM systems, cloud providers, approval systems, policy engines, or risk systems may become normalized assurance inputs.

CAGE consumes those results rather than recreating those systems.

## No Implicit Allow

CAGE Core must never silently create permission merely because no failure was detected.

Missing or invalid evaluation results must not default to ADMITTED.

An ADMITTED Decision must be explicitly produced by the supplied evaluation logic through a valid EvaluationOutcome.

Generic CAGE Core does not prescribe which assurance inputs are mandatory for every business consequence.

Those requirements remain the responsibility of the supplied evaluation logic.

## Decision Proof

A DecisionProof records the Decision and stable references to the assurance inputs supporting it.

It may reference:

* Evidence
* Standing
* Delegation
* Approval
* Context

The proof stores assurance-input identifiers rather than duplicating the entire assurance objects.

A DecisionProof establishes what CAGE decided for an Attempt.

It does not prove that the external consequence became effective.

## Effect Proof

An EffectProof records an Effect assertion.

DecisionProof and EffectProof are distinct assurance records.

A valid DecisionProof must never be interpreted as an EffectProof.

An EffectProof containing EFFECT_UNKNOWN is also different from the complete absence of an EffectProof.

The former means external effect status has been considered but remains unresolved.

The latter means no effect assertion has yet been established.

## Warrant

A CAGE Warrant is the assurance artifact that joins the available proof state for a Consequence.

A minimal Warrant contains:

* warrant identity
* schema version
* DecisionProof
* optional EffectProof
* optional previous Warrant identity

The Warrant derives its:

* consequence identity
* action identity
* attempt identity

from the underlying structural objects rather than duplicating those identities.

A Warrant may legitimately exist before an EffectProof exists.

A later Warrant may reference a previous Warrant to preserve minimal assurance-artifact lineage.

A Warrant must reject a DecisionProof and EffectProof that refer to different Consequences.

## Evidence-Bounded Assurance

CAGE must never make an assurance claim stronger than the available evidence supports.

This principle applies throughout the Core.

Examples include:

* execution failure does not imply NO_BIND
* ADMITTED does not imply BOUND
* REFUSED does not imply NO_BIND
* unresolved external state remains EFFECT_UNKNOWN
* absence of an EffectProof is not treated as an Effect assertion

## Vendor Neutrality

CAGE Core must not depend on:

* AWS
* Azure
* GCP
* MCP
* OpenAI
* Anthropic
* any specific AI model
* any specific agent runtime
* any specific policy language
* any specific IAM platform
* any specific policy engine

External identity, policy, approval, observability, risk, and cloud-security decisions are inputs to CAGE rather than capabilities CAGE should recreate.

## Domain Neutrality

The same Core must support materially different business consequences.

v0.5 demonstrates this using:

* database.delete
* access.grant
* payment.release

No database-specific, access-specific, or payment-specific business logic belongs inside generic CAGE Core.

Domain-specific parameters belong in RequestedEffect data and domain-specific evaluation logic.

## Local Operation

CAGE Core must remain usable locally.

Evaluation and the Core domain contracts must not depend on CAGE Cloud or any hosted CAGE service.

## v0.5 Boundary

v0.5 establishes the Generic Consequence Core.

It includes:

* generic identity and Action contracts
* Consequence identity
* Attempt identity
* generic assurance inputs
* canonical Decision semantics
* canonical Effect semantics
* safe replay
* consequence-level idempotency
* deterministic generic evaluation orchestration
* DecisionProof
* EffectProof
* minimal Warrant foundation
* minimal Attempt and Warrant lineage

v0.5 does not implement:

* CAGE Cloud
* SaaS
* billing
* REST services
* database persistence
* cloud integrations
* MCP integration
* execution credential custody
* protected Effect Adapters
* target-system execution
* authoritative target-state reconciliation
* cryptographic Warrant signatures
* Warrant canonical JSON specification
* independent Warrant verification
* HSM or KMS integration
* post-quantum cryptography
* AI risk intelligence
* enterprise deployment
* a new IAM system
* a new policy language
* full consequence graphs or advanced consequence lineage

Those capabilities belong to later releases.
