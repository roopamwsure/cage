# CAGE

**CAGE — Control Assurance Governance Evaluation**

CAGE is a vendor-neutral assurance layer at the business-consequence boundary for consequential AI and autonomous-agent actions.

CAGE focuses on two distinct questions:

1. **Should this proposed autonomous action be allowed to become a real-world business consequence?**
2. **What can CAGE subsequently prove actually became effective in the external system?**

CAGE does not replace agent runtimes, IAM, authorization systems, policy engines, approval systems, guardrails, workflow systems, observability platforms, SIEM, cloud security controls, or provider execution platforms.

Those systems may become assurance inputs, adapters, evidence sources, execution systems, or verification systems for CAGE.

---

## Status

The v0.7 developer SDK is under development on the feature branch. To run its
local SQLite example from a source checkout, see the
[v0.7 Quickstart](docs/quickstart.md).
See the [integration guide](docs/integration-guide.md) for adapter, verifier,
failure-recovery, and trust-boundary guidance, and the
[release readiness review](docs/v0.7-release-readiness.md) for remaining gates.
For errors and uncertain outcomes, see the
[failure and recovery guide](docs/failure-and-recovery.md).
For portable JSON Warrants and CLI inspection, see the
[portable Warrant guide](docs/portable-warrants-and-cli.md).

Current release:

**v0.6.0 — Consequence Custody**

v0.5 established the Generic Consequence Core: consequence identity, evaluation Attempts, normalized assurance inputs, Decision semantics, Effect semantics, replay, consequence-level idempotency, DecisionProof, EffectProof, and Warrant foundations.

v0.6 extends that model across the controlled execution boundary so CAGE can preserve lineage from Decision through external execution observation, authoritative verification, Effect, and Warrant.

The product remains pre-v1.0. Core semantics are being hardened before provider integrations, SaaS infrastructure, cryptographic signing, or enterprise deployment are added.

---

## Core Idea

Traditional security systems can establish that an authenticated and authorized principal or agent invoked an allowed operation.

CAGE adds a separate assurance layer around the resulting business consequence.

CAGE separates:

1. what was proposed;
2. what was evaluated;
3. what CAGE permitted;
4. what was attempted externally;
5. what the execution system reported;
6. what authoritative verification established;
7. what evidence supports those claims.

The central rule is:

```text
Decision != Effect
```

Related v0.6 separations are:

```text
Evaluation Attempt != ExecutionAttempt
Replay             != Execution Retry
Adapter Result     != Effect
Execution          != Verification
Reconciliation     != Re-execution
```

---

## Core Model

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

A **Consequence** represents one intended business consequence.

An **Attempt** represents one evaluation of that Consequence.

Multiple Attempts may refer to the same Consequence.

v0.6 extends that lineage through custody:

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

## Evaluation Flow

CAGE supports normalized assurance inputs:

- `Evidence`
- `Standing`
- `Delegation`
- `Approval`
- `Context`

The evaluation path is:

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
```

The supplied evaluation logic is responsible for interpreting domain-specific assurance requirements.

Generic CAGE Core does not become a policy language, IAM system, or approval workflow engine.

There is no implicit allow.

---

## Decision States

CAGE defines five canonical Decision states:

- `ADMITTED`
- `HELD`
- `NARROWED`
- `ESCALATED`
- `REFUSED`

A Decision describes what CAGE permitted for a specific evaluation Attempt.

`NO_BIND` is not a Decision state.

---

## Effect States

CAGE defines three canonical Effect states:

- `BOUND`
- `NO_BIND`
- `EFFECT_UNKNOWN`

An Effect describes what authoritative verification has established about the external business consequence.

CAGE must not claim `NO_BIND` merely because:

- execution was not attempted;
- an adapter rejected the request;
- execution returned an error;
- an API timed out;
- a response was lost;
- no acknowledgement was received;
- transport failed.

If external reality cannot be established, the correct state is:

```text
EFFECT_UNKNOWN
```

---

## NARROWED Decisions

A `NARROWED` Decision preserves both:

- the originally requested effect;
- an explicit `permitted_effect`.

For example:

```text
Requested:
Global Admin for 480 minutes

Permitted:
Scoped Operator for 30 minutes
```

Determining whether one effect is semantically more constrained than another is domain-specific and belongs to supplied evaluation logic.

At custody time, only `permitted_effect` may reach the EffectAdapter.

The broader original request must not be executed.

---

## Safe Replay

Replay means re-evaluating the same Consequence using a new evaluation Attempt.

```text
Consequence C1
    |
    +-- Attempt A1 -> ESCALATED
    |
    +-- Attempt A2 -> ADMITTED
```

Replay preserves the original Consequence and business intent.

Replay does **not** execute the external action.

Replay is distinct from execution retry and reconciliation.

---

## Consequence-Level Idempotency

CAGE treats idempotency as business-consequence safety rather than merely HTTP retry handling.

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

Reusing the same idempotency key for materially different business intent results in an explicit conflict.

Current consequence equivalence considers:

- action type;
- principal identity;
- resource identity;
- requested effect.

Attempt identity, agent identity, retry number, replay number, and proposed replacement Consequence identity do not independently create a new Consequence.

---

## Consequence Custody

Consequence Custody is the controlled boundary between a CAGE Decision and external mutation.

Evaluation never automatically executes.

Forbidden:

```text
evaluate_attempt()
    |
    v
ADMITTED
    |
    v
automatic external execution
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

Custody carries an already-created Decision across a controlled execution boundary.

---

## Custody Eligibility

Current custody eligibility is:

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

---

## ExecutionAttempt

`ExecutionAttempt` is distinct from the evaluation `Attempt`.

An evaluation Attempt means:

> one evaluation of a Consequence.

An ExecutionAttempt means:

> one identified attempt to carry an eligible Decision into external execution.

Current ExecutionAttempt lineage includes:

```text
execution_attempt_id
decision
optional previous_execution_attempt_id
```

Execution retry is therefore not the same thing as replay.

---

## ExecutionCapability

`ExecutionCapability` models the structural scope of execution authority.

Current minimal fields are:

```text
capability_id
consequence_id
action_type
resource_id
```

Custody validates that the capability matches:

```text
same consequence_id
same action_type
same resource_id
```

The capability model deliberately does not contain provider credential material such as:

- OAuth tokens;
- API keys;
- passwords;
- cloud credentials;
- IAM policies;
- secrets.

CAGE models execution-authority scope without becoming a credential vault or IAM system.

---

## EffectAdapter

`EffectAdapter` is the vendor-neutral execution boundary.

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

It attempts the external mutation.

It does not decide whether execution is allowed and does not determine Effect truth.

---

## AdapterExecutionResult

The current adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These are request-level execution observations only.

The following mappings are forbidden:

```text
ACKNOWLEDGED != BOUND
REJECTED     != NO_BIND
ERROR        != NO_BIND
UNKNOWN      != EFFECT_UNKNOWN
```

Adapter status cannot substitute for authoritative external-state verification.

---

## Authoritative Verification

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

Verification states are:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

Effect creation is explicit:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

Only an `EffectVerificationResult` can produce an Effect through `create_effect_from_verification()`.

There is deliberately no direct:

```text
AdapterExecutionResult -> Effect
```

conversion.

---

## Reconciliation

Reconciliation re-checks external reality using an existing `AdapterExecutionResult`.

```text
existing AdapterExecutionResult
        |
        v
EffectVerifier
        |
        v
new EffectVerificationResult
```

Reconciliation does not execute.

It does not create an evaluation replay or execution retry.

A typical lineage is:

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

The same Consequence, ExecutionAttempt, and AdapterExecutionResult lineage is preserved.

Reconciliation changes CAGE's knowledge of reality. It does not cause reality to be executed again.

---

## Warrant and Proof Lineage

A CAGE Warrant preserves the available assurance state for a Consequence.

`DecisionProof` and `EffectProof` remain separate.

A Warrant may legitimately exist with:

```text
DecisionProof
EffectProof = absent
```

That state is different from:

```text
DecisionProof
EffectProof(EFFECT_UNKNOWN)
```

`EffectProof` is verification-backed and carries lineage to:

```text
verification_id
adapter_result_id
execution_attempt_id
```

When an EffectProof exists, Warrant derives:

```text
consequence_id
action_id
attempt_id
execution_attempt_id
adapter_result_id
verification_id
```

A later Warrant may reference an earlier Warrant through `previous_warrant_id`.

Earlier assurance history is not rewritten.

---

## Domain Neutrality

The same Generic Consequence Core supports materially different consequence types.

Tests include examples such as:

```text
database.delete
access.grant
payment.release
```

There is no database-specific, access-specific, or payment-specific production logic inside generic CAGE Core.

Domain-specific parameters are carried through `RequestedEffect.parameters` and interpreted by supplied evaluation logic.

---

## Vendor Neutrality

CAGE Core does not depend on:

- AWS
- Azure
- GCP
- MCP
- OpenAI
- Anthropic
- any specific AI model
- any specific agent runtime
- any specific IAM system
- any specific policy engine
- any specific policy language
- any specific execution provider

Provider-specific identity, policy, approval, risk, observability, execution, and security systems should integrate through normalized inputs and external boundaries rather than being recreated inside Core.

---

## Local Operation

CAGE currently has no production runtime dependencies outside the Python standard library.

Requirements:

```text
Python >= 3.11
```

Development uses:

```text
pytest
```

CAGE Core does not require CAGE Cloud or any hosted CAGE service.

---

## Installation for Development

Clone the repository and create a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install CAGE in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the test suite:

```powershell
python -m pytest -q
```

---

## Current Core Modules

```text
action.py
adapter.py
assurance.py
attempt.py
capability.py
consequence.py
custody.py
decision.py
effect.py
evaluation.py
execution.py
idempotency.py
identity.py
replay.py
verification.py
warrant.py
```

---

## v0.6 Scope

v0.6 includes:

- generic Principal, Agent, and Resource identity contracts;
- generic Action and RequestedEffect;
- stable Consequence identity;
- evaluation Attempt identity;
- normalized assurance inputs;
- canonical Decision semantics;
- canonical Effect semantics;
- deterministic evaluation orchestration;
- no-implicit-allow behavior;
- `NARROWED` permitted-effect semantics;
- safe replay;
- consequence-level idempotency;
- DecisionProof;
- ExecutionAttempt identity;
- custody eligibility;
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

---

## Not Included in v0.6

v0.6 does not implement:

- CAGE Cloud;
- SaaS;
- billing;
- REST APIs;
- database persistence;
- AWS-, Azure-, or GCP-specific production adapters;
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

## Documentation

The current architecture is defined in:

```text
docs/architecture.md
docs/invariants.md
docs/v0.6-consequence-custody.md
```

These documents define the intended v0.6 semantic boundary and non-negotiable invariants.

---

## Project Principle

When deciding whether functionality belongs inside CAGE Core, ask:

> Does this preserve CAGE's ability to control whether a consequential autonomous action may cross into external execution and to prove what actually became effective without collapsing identity, evaluation, execution, verification, or proof?

If not, it probably belongs outside generic Core.
