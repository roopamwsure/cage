# CAGE v0.5 Architecture

## Purpose

CAGE is a vendor-neutral consequence-assurance layer for consequential actions taken by AI agents and autonomous systems.

CAGE does not replace agent runtimes, IAM, authorization systems, policy engines, approval systems, guardrails, observability, or cloud security controls.

CAGE operates at the business consequence boundary.

## Core Flow

PROPOSE
? EVALUATE
? DECIDE
? EFFECT
? VERIFY
? WARRANT
? REPLAY / RECONCILE

Decision and Effect are separate dimensions.

## Decision States

CAGE defines five decision states:

- ADMITTED
- HELD
- NARROWED
- ESCALATED
- REFUSED

NO_BIND is not a Decision state.

## Effect States

CAGE defines three effect states:

- BOUND
- NO_BIND
- EFFECT_UNKNOWN

NO_BIND may only be asserted when there are adequate grounds to establish that the intended consequence did not become effective.

An execution error, timeout, missing response, or absence of execution does not by itself prove NO_BIND.

If external reality cannot be established, the state is EFFECT_UNKNOWN.

## Consequence Identity

A Consequence represents one intended business consequence.

Its identity survives:

- evaluation attempts
- retries
- replay
- agent sessions

Multiple attempts may refer to the same Consequence.

## Attempt Identity

Each evaluation has its own Attempt identity.

Replay creates a new Attempt for the same Consequence.

## Replay

Replay means re-evaluating the same proposed Consequence using new or updated assurance inputs.

Replay does not mean automatically executing the external action again.

## Idempotency

Idempotency is enforced at the Consequence level.

The same idempotency key and equivalent consequence must resolve to the same Consequence identity.

Reuse of the same idempotency key for a conflicting consequence must fail.

## Warrant

A CAGE Warrant is the assurance artifact for a Consequence.

The Warrant must distinguish:

- Decision Proof
- Effect Proof

A Warrant must never claim stronger assurance than the available evidence supports.

## Vendor Neutrality

CAGE Core must not depend on:

- AWS
- Azure
- GCP
- MCP
- OpenAI
- Anthropic
- any specific AI model
- any specific agent runtime
- any specific policy language

External identity, policy, approval, observability, and cloud security decisions are inputs to CAGE, not capabilities CAGE should recreate.

## v0.5 Boundary

v0.5 establishes the Generic Consequence Core.

It does not implement:

- cloud integrations
- execution credential custody
- SaaS
- MCP
- post-quantum cryptography
- AI risk intelligence
- enterprise deployment
- a new IAM system
- a new policy language
