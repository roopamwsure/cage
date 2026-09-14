# CAGE v0.5 Definition of Done

CAGE v0.5 is complete only when the Generic Consequence Core satisfies all of the following conditions.

## 1. Domain Neutrality

The same Core models substantially different consequence types, including:

- database.delete
- access.grant
- payment.release

No payment-specific logic exists inside CAGE Core.

## 2. Canonical Decision Semantics

Only these Decision states exist:

- ADMITTED
- HELD
- NARROWED
- ESCALATED
- REFUSED

NO_BIND is not a Decision.

## 3. Canonical Effect Semantics

Only these Effect states exist:

- BOUND
- NO_BIND
- EFFECT_UNKNOWN

Execution failure, timeout, missing response, or absence of execution must not automatically become NO_BIND.

## 4. Consequence Identity

One intended business consequence has one stable Consequence identity.

That identity survives replay, retries, repeated evaluation, and different attempts.

## 5. Attempt Identity

Each evaluation attempt has its own Attempt identity.

Multiple Attempts may refer to the same Consequence.

## 6. Safe Replay

Replay re-evaluates an existing Consequence using a new Attempt.

Replay does not automatically execute the external action again.

## 7. Consequence-Level Idempotency

Equivalent requests using the same idempotency key resolve to the same Consequence identity.

Conflicting consequences using the same idempotency key fail explicitly.

## 8. NARROWED Semantics
CAGE preserves both:

- the originally requested effect
- an explicit permitted effect intended to be more constrained

Determining whether the permitted effect is semantically more constrained is domain-specific and belongs to the supplied evaluation logic.

## 9. Generic Assurance Inputs

The Core supports domain-neutral representations for:

- Principal
- Agent
- Resource
- Standing
- Delegation
- Evidence
- Approval
- Context

## 10. Warrant Foundation

The v0.5 Warrant foundation clearly separates:

- Decision Proof
- Effect Proof

A Decision Proof must not be treated as proof that the external consequence became effective.

## 11. Evidence-Bounded Assurance

CAGE never makes a stronger assurance claim than the available evidence supports.

Unknown effect state remains EFFECT_UNKNOWN.

## 12. Vendor Neutrality

CAGE Core contains no dependency on or assumptions about:

- AWS
- Azure
- GCP
- MCP
- OpenAI
- Anthropic
- any specific agent runtime
- any specific policy engine
- any specific IAM platform

## 13. Local Operation

CAGE Core can operate locally without CAGE Cloud or any hosted CAGE service.

## 14. Tests

Automated tests demonstrate:

- domain neutrality
- Decision and Effect separation
- EFFECT_UNKNOWN handling
- NO_BIND safeguards
- consequence identity stability
- attempt identity
- replay safety
- idempotency conflict handling
- NARROWED behavior
- normalized assurance-input evaluation
- no implicit allow behavior
- Decision Proof assurance references
- Warrant proof separation

All tests must pass before v0.5 is considered complete.

## 15. Scope Discipline

v0.5 does not require:

- CAGE Cloud
- MCP integration
- cloud adapters
- execution credential custody
- protected Effect Adapters
- post-quantum cryptography
- AI intelligence
- enterprise deployment
- full consequence graphs or advanced consequence lineage

Those belong to later releases.
