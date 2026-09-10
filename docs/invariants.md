# CAGE v0.5 Invariants

These invariants define non-negotiable behavior for the Generic Consequence Core.

## Invariant 1 — Decision and Effect are independent

A Decision does not determine the Effect.

For example:

ADMITTED does not imply BOUND.

REFUSED does not, by itself, prove NO_BIND.

## Invariant 2 — NO_BIND requires proof

CAGE must not assert NO_BIND merely because:

- execution was not attempted
- execution returned an error
- an API timed out
- a response was lost
- the agent received no confirmation

NO_BIND requires adequate evidence that the intended business consequence did not become effective.

## Invariant 3 — Uncertainty must remain explicit

If CAGE cannot establish whether a consequence became effective, the Effect is:

EFFECT_UNKNOWN

CAGE must not convert uncertainty into a stronger assurance claim.

## Invariant 4 — Consequence identity is stable

One intended business consequence has one Consequence identity.

The Consequence identity survives:

- retries
- replay
- repeated evaluation
- different execution attempts
- agent session changes

## Invariant 5 — Attempts are distinct

Each evaluation attempt has its own Attempt identity.

Two Attempts may refer to the same Consequence.

## Invariant 6 — Replay is re-evaluation

Replay creates a new Attempt for an existing Consequence.

Replay must not automatically execute the external action.

## Invariant 7 — Idempotency is consequence-level safety

Equivalent requests using the same idempotency key must resolve to the same Consequence identity.

The same idempotency key must not silently represent two materially different consequences.

## Invariant 8 — NARROWED changes the permitted effect

A NARROWED Decision must represent a permitted effect that is more constrained than the requested effect.

The original requested effect must remain preserved for auditability.

## Invariant 9 — Warrant separates decision proof from effect proof

Decision Proof and Effect Proof are different assurance records.

A valid Decision Proof does not automatically establish an Effect Proof.

## Invariant 10 — Core is domain-neutral

CAGE Core must not contain business logic specific to:

- payments
- databases
- access control
- deployment
- procurement
- any other single business domain

Domain-specific parameters belong in generic requested-effect data.

## Invariant 11 — Core is vendor-neutral

CAGE Core must not require:

- AWS
- Azure
- GCP
- MCP
- OpenAI
- Anthropic
- any specific agent framework
- any specific IAM system
- any specific policy engine

Provider-specific information must enter CAGE through normalized contracts.

## Invariant 12 — No implicit allow

Missing, invalid, incomplete, or untrusted assurance inputs must never silently produce permission for a consequential action.

## Invariant 13 — Assurance claims are evidence-bounded

CAGE must never make an assurance claim stronger than the evidence available to support it.

## Invariant 14 — External execution is outside v0.5 Core

v0.5 models consequence assurance semantics.

It does not yet provide credential custody, protected execution adapters, or target-system execution.

## Invariant 15 — The Core must remain locally usable

CAGE Core must not depend on CAGE Cloud or any external hosted service in order to evaluate its own domain contracts.
