# CAGE v0.5 Invariants

These invariants define non-negotiable behavior for the Generic Consequence Core.

## Invariant 1 — Decision and Effect are independent

A Decision does not determine the Effect.

For example:

ADMITTED does not imply BOUND.

REFUSED does not, by itself, prove NO_BIND.

## Invariant 2 — NO_BIND requires proof

CAGE must not assert NO_BIND merely because:

* execution was not attempted
* execution returned an error
* an API timed out
* a response was lost
* the agent received no confirmation

NO_BIND requires adequate evidence that the intended business consequence did not become effective.

## Invariant 3 — Uncertainty must remain explicit

If CAGE cannot establish whether a consequence became effective, the Effect is:

EFFECT_UNKNOWN

CAGE must not convert uncertainty into a stronger assurance claim.

## Invariant 4 — Consequence identity is stable

One intended business consequence has one Consequence identity.

The Consequence identity survives:

* retries
* replay
* repeated evaluation
* different execution attempts
* agent session changes

A new Attempt does not, by itself, create a new Consequence.

## Invariant 5 — Attempts are distinct

Each evaluation attempt has its own Attempt identity.

Multiple Attempts may refer to the same Consequence.

An Attempt may reference the identity of a previous Attempt to preserve replay lineage.

## Invariant 6 — Replay is re-evaluation

Replay creates a new Attempt for an existing Consequence.

Replay must preserve the original Consequence and original business intent.

Replay must not automatically execute the external action.

Replay may produce a different Decision if the assurance inputs available to the new Attempt differ.

## Invariant 7 — Idempotency is consequence-level safety

Equivalent requests using the same idempotency key must resolve to the same Consequence identity.

The same idempotency key must not silently represent two materially different consequences.

Conflicting consequence semantics associated with the same idempotency key must fail explicitly.

## Invariant 8 — NARROWED carries an explicit permitted effect

A NARROWED Decision must carry an explicit permitted effect intended to be more constrained than the originally requested effect.

The original requested effect must remain preserved for auditability.

Determining whether one effect is more constrained than another is domain-specific and belongs to the supplied evaluation logic rather than generic CAGE Core.

## Invariant 9 — Warrant separates Decision Proof from Effect Proof

DecisionProof and EffectProof are different assurance records.

A valid DecisionProof does not automatically establish an EffectProof.

A Warrant may legitimately contain a DecisionProof while no EffectProof exists yet.

Absence of an EffectProof is different from an EffectProof whose Effect state is EFFECT_UNKNOWN.

## Invariant 10 — Core is domain-neutral

CAGE Core must not contain business logic specific to:

* payments
* databases
* access control
* deployment
* procurement
* any other single business domain

Domain-specific parameters belong in generic RequestedEffect data.

Domain-specific evaluation semantics belong in supplied evaluation logic rather than generic CAGE Core.

The same generic Core must support materially different consequence types.

## Invariant 11 — Core is vendor-neutral

CAGE Core must not require or embed assumptions about:

* AWS
* Azure
* GCP
* MCP
* OpenAI
* Anthropic
* any specific AI model
* any specific agent framework
* any specific IAM system
* any specific policy engine
* any specific policy language

Provider-specific information must enter CAGE through normalized contracts.

External identity, policy, approval, observability, risk, and cloud-security systems provide inputs to CAGE rather than capabilities CAGE should recreate.

## Invariant 12 — No implicit allow

Missing, invalid, incomplete, or untrusted assurance inputs must never cause CAGE Core to implicitly produce permission for a consequential action.

An ADMITTED Decision must be explicitly returned by the supplied evaluation logic through a valid EvaluationOutcome.

A missing or invalid EvaluationOutcome must fail rather than default to ADMITTED.

Generic CAGE Core does not prescribe which assurance inputs are mandatory for every consequence.

Those requirements belong to the supplied evaluation logic.

## Invariant 13 — Assurance claims are evidence-bounded

CAGE must never make an assurance claim stronger than the available evidence supports.

Examples include:

* ADMITTED does not imply BOUND
* REFUSED does not imply NO_BIND
* execution failure does not imply NO_BIND
* timeout does not imply NO_BIND
* missing response does not imply NO_BIND
* unresolved external state remains EFFECT_UNKNOWN
* absence of an EffectProof is not treated as an Effect assertion

## Invariant 14 — External execution is outside v0.5 Core

v0.5 models consequence-assurance semantics.

It does not provide:

* credential custody
* protected execution adapters
* target-system execution
* cloud-specific executors
* authoritative target-state reconciliation

Evaluation must not execute the external action or create an Effect merely because a Decision was produced.

## Invariant 15 — The Core must remain locally usable

CAGE Core must operate locally without CAGE Cloud or any external hosted CAGE service.

Its domain models, evaluation orchestration, replay semantics, idempotency behavior, and proof foundation must not require network access or a hosted CAGE dependency.

## Invariant 16 — Evaluation consumes normalized assurance inputs

Evaluation may consume normalized:

* Evidence
* Standing
* Delegation
* Approval
* Context

These objects represent passive assurance facts or signals.

They must not themselves become authorization engines, execution mechanisms, or approval workflows.

The supplied evaluation logic interprets those inputs and returns an explicit EvaluationOutcome.

## Invariant 17 — Evaluation is attempt-scoped

Evaluation occurs against an Attempt rather than directly against an Action alone.

A Decision belongs to the Attempt that produced it.

The same Consequence may therefore receive different Decisions across different Attempts while preserving one stable Consequence identity.

For example:

* Attempt 1 may produce ESCALATED
* Attempt 2 may later produce ADMITTED

Both Attempts may still refer to the same Consequence.

## Invariant 18 — Decision Proof records assurance provenance

A DecisionProof records the Decision together with stable references to the assurance inputs supporting that Decision.

Those references may include:

* Evidence identifiers
* Standing identifiers
* Delegation identifiers
* Approval identifiers
* Context identifiers

DecisionProof does not establish what became true in the external world.

## Invariant 19 — Effect Proof requires independent effect establishment

EffectProof represents an assertion about the external consequence.

It must remain independent from the DecisionProof.

CAGE must not manufacture an Effect solely from the Decision state.

In particular:

* ADMITTED must not create BOUND
* REFUSED must not create NO_BIND
* absence of execution must not create NO_BIND

Effect claims must remain bounded by the available verification basis.

## Invariant 20 — v0.5 scope remains disciplined

v0.5 establishes the Generic Consequence Core.

It does not require:

* CAGE Cloud
* SaaS
* billing
* REST APIs
* database persistence
* cloud integrations
* MCP integration
* execution credential custody
* protected Effect Adapters
* target-system execution
* authoritative reconciliation
* cryptographic Warrant signatures
* canonical Warrant JSON
* independent Warrant verification
* HSM or KMS integration
* post-quantum cryptography
* AI risk intelligence
* enterprise deployment
* a new IAM system
* a new policy language
* full consequence graphs
* advanced consequence lineage

Those capabilities belong to later releases.
